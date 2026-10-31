"""History page: commit graph, search, commit details and file diffs."""
from __future__ import annotations

import html
import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QSplitter, QTableView,
                               QTextBrowser, QVBoxLayout, QWidget)

from ...common.i18n import t
from ...core.models import Commit, FileChange
from ...core.runner import GitError
from .. import theme
from ..display import STATUS_COLOR, avatar_color
from ..widgets.commit_graph import GraphDelegate, HistoryModel
from ..widgets.diff_view import DiffView

if TYPE_CHECKING:
    from ..repo.view import RepoView


SEARCH_MODES = ["filter", "message", "author", "content", "path"]


class HistoryPage(QWidget):
    def __init__(self, rw: "RepoView"):
        super().__init__()
        self.rw = rw
        self._ctx: tuple = ()  # (sha, parents)
        self._hit_list: list[int] = []
        self._hit_pos = -1
        self.searching = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        bar = QHBoxLayout()
        self.mode = QComboBox()
        for m in SEARCH_MODES:
            self.mode.addItem(t(f"hist.search.{m}"), m)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 " + t("hist.search_hint"))
        self.search.setClearButtonEnabled(True)
        self.all_branches = QCheckBox(t("hist.all_branches"))
        self.all_branches.setChecked(True)
        self.first_parent = QCheckBox(t("hist.graph"))
        self.first_parent.setChecked(True)
        self.hits = QLabel("")
        self.hits.setObjectName("muted")
        bar.addWidget(self.mode)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.hits)
        bar.addWidget(self.first_parent)
        bar.addWidget(self.all_branches)
        lay.addLayout(bar)

        vs = QSplitter(Qt.Vertical)
        lay.addWidget(vs, 1)
        self.model = HistoryModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setItemDelegate(GraphDelegate(self.model, self.table))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for c, w in ((1, 170), (2, 120), (3, 90)):
            hh.setSectionResizeMode(c, QHeaderView.Interactive)
            self.table.setColumnWidth(c, w)
        vs.addWidget(self.table)
        vs.addWidget(self._build_detail())
        vs.setSizes([440, 380])

        self.table.selectionModel().selectionChanged.connect(lambda *_: self._sel_changed())
        self.table.customContextMenuRequested.connect(self._menu)
        self.search.textChanged.connect(self._text_changed)
        self.search.returnPressed.connect(self._enter)
        self.mode.currentIndexChanged.connect(lambda _: self._mode_changed())
        self.all_branches.toggled.connect(lambda _: self.rw.refresh(force_log=True))
        self.first_parent.toggled.connect(lambda _: self.rw.refresh(force_log=True))
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: (self.search.setFocus(), self.search.selectAll()))
        QShortcut(QKeySequence("F3"), self, self._next_hit)

    def _build_detail(self) -> QWidget:
        hs = QSplitter(Qt.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.info = QTextBrowser()
        self.info.setOpenLinks(False)
        self.info.anchorClicked.connect(self._anchor)
        self.files = QListWidget()
        self.files.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files.currentItemChanged.connect(lambda *_: self._show_file())
        self.files.customContextMenuRequested.connect(self._file_menu)
        ll.addWidget(self.info, 3)
        ll.addWidget(self.files, 4)
        hs.addWidget(left)
        self.diff = DiffView()
        self.diff.optionsChanged.connect(self._show_file)
        hs.addWidget(self.diff)
        hs.setSizes([440, 900])
        hs.setStretchFactor(1, 1)
        return hs

    @property
    def search_mode(self) -> str:
        return self.mode.currentData()

    def set_commits(self, commits: list[Commit], head: str, remotes: set[str], graph: bool = True):
        keep = self.selected_commits()
        self.model.set_commits(commits, head, remotes, graph)
        if self.search_mode == "filter":
            self._do_filter(self.search.text())
        if keep and self.select_sha(keep[0].sha, quiet=True):
            return
        if commits and not keep:
            self.table.selectRow(0)
            return
        self.info.clear()
        self.files.clear()
        self.diff.clear()

    def select_sha(self, sha: str, quiet: bool = False) -> bool:
        for i, c in enumerate(self.model.commits):
            if c.sha.startswith(sha):
                self.table.selectRow(i)
                self.table.scrollTo(self.model.index(i, 0), QAbstractItemView.PositionAtCenter)
                return True
        if not quiet:
            self.rw.main.status(t("hist.not_loaded", sha=sha[:8]))
        return False

    def selected_commits(self) -> list[Commit]:
        rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()})
        return [self.model.commits[r] for r in rows if r < len(self.model.commits)]

    # ---------------------------------------------------------------- search
    def _mode_changed(self):
        if self.searching and self.search_mode == "filter":
            self.searching = False
            self.rw.refresh(force_log=True)
        self._text_changed(self.search.text())

    def _text_changed(self, q: str):
        if self.search_mode == "filter":
            self._do_filter(q)
        elif not q and self.searching:
            self.searching = False
            self.hits.setText("")
            self.rw.refresh(force_log=True)

    def _enter(self):
        if self.search_mode == "filter":
            self._next_hit()
            return
        q = self.search.text().strip()
        if not q:
            return
        self.searching = True
        self.rw.deep_search(q, self.search_mode)

    def show_search_results(self, commits: list[Commit]):
        self.model.set_commits(commits, self.rw.repo.head_sha(), set(self.rw.repo.remotes()), graph=False)
        self.hits.setText(t("hist.results", n=len(commits)))
        if commits:
            self.table.selectRow(0)

    def _do_filter(self, q: str):
        q = q.strip().lower()
        self.model.highlight = set()
        self.model.dim = set()
        self._hit_list = []
        self._hit_pos = -1
        if q:
            for i, c in enumerate(self.model.commits):
                hay = " ".join([c.subject, c.author, c.email, c.sha, *c.refs]).lower()
                if q in hay:
                    self._hit_list.append(i)
            self.model.highlight = set(self._hit_list)
            self.model.dim = set(range(len(self.model.commits))) - self.model.highlight
            self.hits.setText(t("hist.hits", n=len(self._hit_list)))
        else:
            self.hits.setText("")
        self.table.viewport().update()
        if self._hit_list:
            self._next_hit()

    def _next_hit(self):
        if not self._hit_list:
            return
        self._hit_pos = (self._hit_pos + 1) % len(self._hit_list)
        r = self._hit_list[self._hit_pos]
        self.table.selectRow(r)
        self.table.scrollTo(self.model.index(r, 0), QAbstractItemView.PositionAtCenter)
        self.hits.setText(t("hist.hit_pos", i=self._hit_pos + 1, n=len(self._hit_list)))

    # ---------------------------------------------------------------- detail
    def _anchor(self, url):
        s = url.toString()
        if s.startswith("copy:"):
            QApplication.clipboard().setText(s[5:])
            self.rw.main.status(t("common.copied"))
        else:
            self.select_sha(s)

    def _sel_changed(self):
        sel = self.selected_commits()
        if not sel:
            return
        repo = self.rw.repo
        if len(sel) >= 2:
            newest, oldest = sel[0], sel[-1]
            self._ctx = (newest.sha, [oldest.sha])
            self.info.setHtml(self._card(t("hist.compare_two", a=oldest.short, b=newest.short), "", ""))
            self._fill_files(repo.range_files(oldest.sha, newest.sha))
            return
        c = sel[0]
        try:
            info = repo.commit_info(c.sha)
        except GitError as e:
            self.info.setPlainText(str(e))
            return
        self._ctx = (c.sha, info["parents"])
        C = theme.C
        parents = " ".join(f"<a href='{p}' style='color:{C['accent2']}'>{p[:8]}</a>" for p in info["parents"])
        body = html.escape(info.get("body", "").strip()).replace("\n", "<br>")
        col = avatar_color(info.get("email") or info.get("author", ""))
        refs = "".join(f"<span style='background:{C['panel2']};color:{C['accent2']};'>&nbsp;{html.escape(r)}&nbsp;</span> "
                       for r in c.refs)
        meta = (f"<table cellspacing=3 style='color:{C['muted']}'>"
                f"<tr><td>{t('hist.author')}</td><td><b style='color:{col}'>{html.escape(info['author'])}</b> "
                f"&lt;{html.escape(info['email'])}&gt;</td></tr>"
                f"<tr><td>{t('hist.date')}</td><td>{info['date']}</td></tr>"
                + (f"<tr><td>{t('hist.committer')}</td><td>{html.escape(info['committer'])} · {info['cdate']}</td></tr>"
                   if info['committer'] != info['author'] else "")
                + f"<tr><td>SHA</td><td><a href='copy:{info['sha']}' style='color:{C['accent2']}'>{info['sha']}</a></td></tr>"
                + (f"<tr><td>{t('hist.parents')}</td><td>{parents}</td></tr>" if parents else "")
                + (f"<tr><td>{t('hist.contained')}</td><td>{html.escape(info['contains'])}</td></tr>"
                   if info.get("contains") and info["contains"] != info["sha"][:len(info["contains"])] else "")
                + "</table>")
        self.info.setHtml(self._card(body, refs, meta))
        self._fill_files(repo.commit_files(c.sha, info["parents"]))

    @staticmethod
    def _card(body: str, refs: str, meta: str) -> str:
        C = theme.C
        return (f"<div style='color:{C['text']}'>{refs}<div style='font-size:14px;font-weight:600;margin:6px 0'>{body}</div>"
                f"{meta}</div>")

    def _fill_files(self, files: list[FileChange]):
        self.files.blockSignals(True)
        self.files.clear()
        for fc in files:
            label = f"{fc.orig_path} → {fc.path}" if fc.orig_path else fc.path
            it = QListWidgetItem(f"{fc.x}   {label}")
            it.setForeground(QColor(STATUS_COLOR.get(fc.x, theme.C["text"])))
            it.setData(Qt.UserRole, fc)
            self.files.addItem(it)
        self.files.blockSignals(False)
        if self.files.count():
            self.files.setCurrentRow(0)
        else:
            self.diff.clear(t("diff.no_content"))

    def _show_file(self):
        it = self.files.currentItem()
        if not it or not self._ctx:
            return
        fc = it.data(Qt.UserRole)
        sha, parents = self._ctx
        data = self.rw.repo.commit_diff(sha, parents, fc, self.diff.context, self.diff.ignore_ws)
        self.diff.set_diff(data, "readonly", fc.path)

    def _file_menu(self, pos):
        it = self.files.itemAt(pos)
        if not it or not self._ctx:
            return
        fc: FileChange = it.data(Qt.UserRole)
        sha = self._ctx[0]
        rw = self.rw
        m = QMenu(self)
        m.addAction(t("file.history"), lambda: rw.file_history(fc.path))
        m.addAction(t("file.blame_at"), lambda: rw.blame(fc.path, sha))
        m.addAction(t("file.restore_from", sha=sha[:8]), lambda: rw.restore_file(sha, fc.path))
        m.addAction(t("file.save_as"), lambda: rw.save_file_at(sha, fc.path))
        m.addAction(t("file.full_diff"), lambda: rw.show_full_diff(sha, self._ctx[1]))
        m.addSeparator()
        full = os.path.join(rw.repo.path, fc.path)
        m.addAction(t("file.open_editor"), lambda: rw.open_in_editor(full))
        m.addAction(t("file.copy_path"), lambda: QApplication.clipboard().setText(fc.path))
        m.exec(self.files.mapToGlobal(pos))

    def _menu(self, pos):
        sel = self.selected_commits()
        if not sel:
            return
        rw = self.rw
        c = sel[0]
        m = QMenu(self)
        if len(sel) == 1:
            m.addAction("⎇  " + t("hist.checkout"), lambda: rw.checkout_commit(c))
            m.addAction("＋ " + t("branch.new_here"), lambda: rw.new_branch(c.sha, c.short + " " + c.subject))
            m.addAction("◆  " + t("tag.new_here"), lambda: rw.new_tag(c.sha, c.short + " " + c.subject))
            m.addSeparator()
            m.addAction(t("hist.merge_this"), lambda: rw.merge(preset=c.sha))
            m.addAction(t("hist.rebase_onto"), lambda: rw.rebase_onto(c.sha, c.short))
            m.addAction(t("hist.irebase"), lambda: rw.interactive_rebase(c))
            m.addSeparator()
        m.addAction("🍒 " + t("hist.cherry_pick", n=len(sel)), lambda: rw.cherry_pick(sel))
        if len(sel) == 1:
            m.addAction(t("hist.revert"), lambda: rw.revert(c))
            m.addAction(t("hist.reset"), lambda: rw.reset_to(c))
            m.addSeparator()
            bm = m.addMenu("🔬 Bisect")
            st = rw.repo.state()
            if st.bisecting:
                bm.addAction(t("bisect.good"), lambda: rw.bisect("good"))
                bm.addAction(t("bisect.bad"), lambda: rw.bisect("bad"))
                bm.addAction(t("bisect.skip"), lambda: rw.bisect("skip"))
                bm.addAction(t("bisect.reset"), lambda: rw.bisect("reset"))
            else:
                bm.addAction(t("bisect.start_here"), lambda: rw.bisect_start(c.sha))
        m.addSeparator()
        if len(sel) == 2:
            m.addAction(t("hist.compare_sel"), lambda: rw.compare(sel[-1].sha, sel[0].sha))
        m.addAction(t("hist.patch", n=len(sel)), lambda: rw.format_patch(sel))
        if len(sel) == 1:
            m.addAction(t("hist.archive"), lambda: rw.archive(c.sha))
            m.addAction(t("hist.open_web"), lambda: rw.open_commit_web(c.sha))
        cm = m.addMenu(t("common.copy"))
        cm.addAction("SHA", lambda: QApplication.clipboard().setText("\n".join(x.sha for x in sel)))
        cm.addAction(t("hist.copy_short"), lambda: QApplication.clipboard().setText("\n".join(x.short for x in sel)))
        cm.addAction(t("hist.copy_msg"), lambda: QApplication.clipboard().setText("\n".join(x.subject for x in sel)))
        m.exec(self.table.viewport().mapToGlobal(pos))
