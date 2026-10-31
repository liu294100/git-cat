"""Files page: browse the project at any revision, view code, search contents, compare file versions."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QSplitter, QStackedWidget, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ...common.i18n import t
from ...common.system import open_path, reveal_in_explorer
from .. import theme
from ..dialogs.version_compare import WT, VersionCompareDialog
from ..widgets.code_view import CodeView

if TYPE_CHECKING:
    from ..repo.view import RepoView

ROLE_PATH = Qt.UserRole
MAX_TREE_ITEMS = 60000


class FilesPage(QWidget):
    def __init__(self, rw: "RepoView"):
        super().__init__()
        self.rw = rw
        self.files: list[str] = []
        self.marked: Optional[tuple[str, str]] = None  # (rev, path) chosen as left side
        self.loaded_rev: Optional[str] = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        bar = QHBoxLayout()
        bar.addWidget(QLabel(t("files.revision")))
        self.rev = QComboBox()
        self.rev.setEditable(True)
        self.rev.setMinimumWidth(260)
        bar.addWidget(self.rev)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("🔎 " + t("files.filter"))
        self.filter.setClearButtonEnabled(True)
        bar.addWidget(self.filter, 1)
        self.grep_box = QCheckBox(t("files.search_content"))
        self.regex = QCheckBox("Regex")
        self.case = QCheckBox("Aa")
        self.case.setToolTip(t("files.case"))
        for w in (self.grep_box, self.regex, self.case):
            bar.addWidget(w)
        cmp_btn = QPushButton("⇄ " + t("cmpv.title"))
        cmp_btn.clicked.connect(lambda: self.compare_dialog(self.current_path() or ""))
        bar.addWidget(cmp_btn)
        self.count = QLabel("")
        self.count.setObjectName("muted")
        bar.addWidget(self.count)
        lay.addLayout(bar)

        split = QSplitter(Qt.Horizontal)
        left = QStackedWidget()
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.flat = QListWidget()
        self.flat.setUniformItemSizes(True)
        self.flat.setContextMenuPolicy(Qt.CustomContextMenu)
        self.hits = QListWidget()
        self.hits.setContextMenuPolicy(Qt.CustomContextMenu)
        for w in (self.tree, self.flat, self.hits):
            left.addWidget(w)
        self.left = left
        split.addWidget(left)
        self.view = CodeView()
        split.addWidget(self.view)
        split.setSizes([380, 1000])
        split.setStretchFactor(1, 1)
        lay.addWidget(split, 1)

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(250)
        self._filter_timer.timeout.connect(self._apply_filter)
        self.filter.textChanged.connect(lambda _: self._filter_timer.start())
        self.filter.returnPressed.connect(self._apply_filter)
        self.grep_box.toggled.connect(lambda _: self._apply_filter())
        self.rev.activated.connect(lambda _: self.load())
        self.rev.lineEdit().returnPressed.connect(self.load)
        self.tree.currentItemChanged.connect(lambda it, _: self._open(it.data(0, ROLE_PATH) if it else None))
        self.flat.currentItemChanged.connect(lambda it, _: self._open(it.data(ROLE_PATH) if it else None))
        self.hits.currentItemChanged.connect(lambda it, _: it and self._open_hit(it))
        for w in (self.tree, self.flat, self.hits):
            w.customContextMenuRequested.connect(lambda pos, w=w: self._menu(w, pos))

    # ---------------------------------------------------------------- data
    @property
    def revision(self) -> str:
        i = self.rev.currentIndex()
        if i >= 0 and self.rev.itemText(i) == self.rev.currentText():
            return self.rev.itemData(i) or WT
        return self.rev.currentText().strip()

    def showEvent(self, e):
        super().showEvent(e)
        if self.loaded_rev is None:
            self._fill_revs()
            self.load()

    def _fill_revs(self):
        cur = self.revision if self.rev.count() else WT
        self.rev.blockSignals(True)
        self.rev.clear()
        self.rev.addItem("📝 " + t("files.worktree"), WT)
        self.rev.addItem("HEAD", "HEAD")
        for r in self.rw.repo.all_refs_for_picker():
            self.rev.addItem(r, r)
        i = self.rev.findData(cur)
        self.rev.setCurrentIndex(max(0, i))
        self.rev.blockSignals(False)

    def reload_if_worktree(self):
        if self.isVisible() and self.revision == WT:
            self.load()

    def load(self):
        rev, repo = self.revision, self.rw.repo
        self.loaded_rev = rev

        def done(files):
            if rev != self.revision:
                return
            self.files = files
            self._build_tree()
            self._apply_filter()
        self.rw.bg(lambda: repo.list_files(rev), done, lambda e: self.view.clear(str(e)), t("files.loading"))

    def _build_tree(self):
        keep = self.current_path()
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        folders: dict[str, QTreeWidgetItem] = {}
        bold = QFont()
        bold.setBold(True)
        muted = theme.color("muted")
        root = self.tree.invisibleRootItem()
        for p in self.files[:MAX_TREE_ITEMS]:
            parent = root
            parts = p.split("/")
            acc = ""
            for d in parts[:-1]:
                acc = f"{acc}/{d}" if acc else d
                node = folders.get(acc)
                if node is None:
                    node = QTreeWidgetItem(["📁 " + d])
                    node.setForeground(0, muted)
                    parent.addChild(node)
                    folders[acc] = node
                parent = node
            leaf = QTreeWidgetItem([_icon(parts[-1]) + " " + parts[-1]])
            leaf.setData(0, ROLE_PATH, p)
            parent.addChild(leaf)
        _sort_tree(root)
        self.tree.setUpdatesEnabled(True)
        if keep:
            self.select_path(keep)

    def _apply_filter(self):
        q = self.filter.text().strip()
        if self.grep_box.isChecked() and q:
            self._grep(q)
            return
        if not q:
            self.left.setCurrentWidget(self.tree)
            self.count.setText(t("files.count", n=len(self.files)))
            return
        ql = q.lower()
        matches = [p for p in self.files if ql in p.lower()][:5000]
        self.flat.clear()
        for p in matches:
            it = QListWidgetItem(f"{_icon(p)} {os.path.basename(p)}    {os.path.dirname(p)}")
            it.setData(ROLE_PATH, p)
            self.flat.addItem(it)
        self.left.setCurrentWidget(self.flat)
        self.count.setText(t("files.count", n=len(matches)))

    def _grep(self, q: str):
        rev, repo = self.revision, self.rw.repo
        regex, case = self.regex.isChecked(), self.case.isChecked()

        def done(res):
            self.hits.clear()
            for path, line, text in res:
                it = QListWidgetItem(f"{path}:{line}   {text.strip()[:160]}")
                it.setData(ROLE_PATH, (path, line))
                self.hits.addItem(it)
            self.left.setCurrentWidget(self.hits)
            self.count.setText(t("hist.results", n=len(res)))
        self.rw.bg(lambda: repo.grep(q, rev, not case, regex), done, lambda e: self.count.setText(str(e)[:80]),
                   t("files.searching"))

    # ---------------------------------------------------------------- viewing
    def current_path(self) -> Optional[str]:
        w = self.left.currentWidget()
        if w is self.tree:
            it = self.tree.currentItem()
            return it.data(0, ROLE_PATH) if it else None
        it = w.currentItem()
        if not it:
            return None
        d = it.data(ROLE_PATH)
        return d[0] if isinstance(d, tuple) else d

    def select_path(self, path: str):
        self.filter.clear()
        self.left.setCurrentWidget(self.tree)
        it = self.tree.invisibleRootItem()
        for part in path.split("/"):
            nxt = None
            for i in range(it.childCount()):
                ch = it.child(i)
                if ch.text(0).split(" ", 1)[-1] == part:
                    nxt = ch
                    break
            if nxt is None:
                return
            it.setExpanded(True)
            it = nxt
        self.tree.setCurrentItem(it)
        self.tree.scrollToItem(it)

    def _open(self, path: Optional[str], line: int = 0):
        if not path:
            return
        rev, repo = self.revision, self.rw.repo

        def done(data: bytes):
            self.view.show_bytes(data, f"{path}   @ {rev or t('files.worktree')}")
            if line:
                self.view.edit.goto_line(line)
        self.rw.bg(lambda: repo.read_file(rev, path), done, lambda e: self.view.clear(str(e)), "")

    def _open_hit(self, it: QListWidgetItem):
        path, line = it.data(ROLE_PATH)
        self._open(path, line)

    # ---------------------------------------------------------------- actions
    def compare_dialog(self, path: str, rev_a: str = "HEAD", path_b: Optional[str] = None, rev_b: str = WT):
        VersionCompareDialog(self.rw, path, rev_a, path_b, rev_b).exec()

    def _menu(self, w, pos):
        path = self.current_path()
        if not path:
            return
        rev = self.revision
        rw = self.rw
        full = os.path.join(rw.repo.path, path)
        m = QMenu(self)
        m.addAction("⇄ " + t("files.cmp_worktree"), lambda: self.compare_dialog(path, rev or "HEAD", path, WT))
        m.addAction("⇄ " + t("files.cmp_head"), lambda: self.compare_dialog(path, "HEAD", path, rev))
        m.addAction("⇄ " + t("files.cmp_pick"), lambda: self.compare_dialog(path, rev or "HEAD"))
        if self.marked:
            mr, mp = self.marked
            m.addAction("⇄ " + t("files.cmp_marked", p=f"{os.path.basename(mp)}@{mr or 'WT'}"),
                        lambda: self.compare_dialog(mp, mr, path, rev))
        m.addAction("☑ " + t("files.mark"), lambda: self._mark(rev, path))
        m.addSeparator()
        m.addAction(t("file.history"), lambda: rw.file_history(path))
        m.addAction(t("file.blame"), lambda: rw.blame(path, rev))
        if rev:
            m.addAction(t("file.restore_from", sha=rev[:12]), lambda: rw.restore_file(rev, path))
            m.addAction(t("file.save_as"), lambda: rw.save_file_at(rev, path))
        m.addSeparator()
        m.addAction(t("file.open_editor"), lambda: rw.open_in_editor(full))
        m.addAction(t("file.open"), lambda: open_path(full) if os.path.exists(full) else None)
        m.addAction(t("file.reveal"), lambda: reveal_in_explorer(full))
        m.addAction(t("file.copy_path"), lambda: QApplication.clipboard().setText(path))
        m.addAction(t("files.copy_abs"), lambda: QApplication.clipboard().setText(full))
        m.exec(w.viewport().mapToGlobal(pos))

    def _mark(self, rev: str, path: str):
        self.marked = (rev, path)
        self.rw.main.toast(t("files.marked", p=f"{path} @ {rev or t('files.worktree')}"))


_EXT_ICON = {".py": "🐍", ".js": "📜", ".ts": "📘", ".tsx": "📘", ".jsx": "📜", ".java": "☕", ".kt": "🟣", ".go": "🐹",
             ".rs": "🦀", ".c": "🔧", ".h": "🔧", ".cpp": "🔧", ".cs": "🟪", ".rb": "💎", ".php": "🐘", ".swift": "🕊",
             ".md": "📝", ".txt": "📄", ".json": "🧾", ".yml": "⚙", ".yaml": "⚙", ".toml": "⚙", ".ini": "⚙",
             ".xml": "🧾", ".html": "🌐", ".css": "🎨", ".scss": "🎨", ".vue": "💚", ".sql": "🗃", ".sh": "💲",
             ".bat": "💲", ".cmd": "💲", ".ps1": "💲", ".png": "🖼", ".jpg": "🖼", ".gif": "🖼", ".svg": "🖼",
             ".ico": "🖼", ".zip": "📦", ".lock": "🔒"}


def _sort_tree(node: QTreeWidgetItem) -> None:
    """Folders first, then files; each group case-insensitively by name (icon prefix ignored)."""
    kids = node.takeChildren()
    kids.sort(key=lambda it: (it.data(0, ROLE_PATH) is not None, it.text(0).split(" ", 1)[-1].lower()))
    node.addChildren(kids)
    for k in kids:
        if k.childCount():
            _sort_tree(k)


def _icon(name: str) -> str:
    return _EXT_ICON.get(os.path.splitext(name)[1].lower(), "📄")
