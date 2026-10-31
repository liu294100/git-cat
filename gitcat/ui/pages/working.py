"""Working-copy page: unstaged/staged lists, interactive diff, commit box."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget)

from ...common.i18n import t
from ...common.system import open_path, reveal_in_explorer
from ...core.models import FileChange
from ...core.runner import GitError
from .. import theme
from ..widgets.common import FileList, header, small_button
from ..widgets.diff_view import DiffView

if TYPE_CHECKING:
    from ..repo.view import RepoView


class WorkingPage(QWidget):
    def __init__(self, rw: "RepoView"):
        super().__init__()
        self.rw = rw
        self.active: Optional[FileList] = None
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split)
        vs = QSplitter(Qt.Vertical)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(6, 6, 2, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("🔎 " + t("work.filter"))
        self.filter.setClearButtonEnabled(True)
        ll.addWidget(self.filter)
        b_stage_sel = small_button("＋", t("work.stage_sel"))
        b_stage_all = small_button(t("work.stage_all"))
        b_discard = small_button("↺", t("work.discard"), "danger")
        h1, self.lbl_unstaged = header(t("work.unstaged"), b_stage_sel, b_stage_all, b_discard)
        ll.addLayout(h1)
        self.unstaged = FileList()
        ll.addWidget(self.unstaged)
        vs.addWidget(left)

        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        l2.setContentsMargins(6, 4, 2, 0)
        b_unstage_sel = small_button("－", t("work.unstage_sel"))
        b_unstage_all = small_button(t("work.unstage_all"))
        h2, self.lbl_staged = header(t("work.staged"), b_unstage_sel, b_unstage_all)
        l2.addLayout(h2)
        self.staged = FileList()
        l2.addWidget(self.staged)
        vs.addWidget(w2)

        vs.addWidget(self._build_commit_box())
        vs.setSizes([340, 220, 250])
        split.addWidget(vs)
        self.diff = DiffView(interactive=True)
        self.diff.applier = self._apply_patch
        self.diff.optionsChanged.connect(self.show_current)
        split.addWidget(self.diff)
        split.setSizes([460, 900])
        split.setStretchFactor(1, 1)

        self.filter.textChanged.connect(lambda s: (self.unstaged.set_filter(s), self.staged.set_filter(s)))
        b_stage_sel.clicked.connect(lambda: rw.stage(self.unstaged.selected()))
        b_stage_all.clicked.connect(lambda: rw.stage(self.unstaged.all_visible()) if self.filter.text()
                                    else rw.stage_all())
        b_discard.clicked.connect(lambda: rw.discard(self.unstaged.selected()))
        b_unstage_sel.clicked.connect(lambda: rw.unstage(self.staged.selected()))
        b_unstage_all.clicked.connect(rw.unstage_all)
        self.unstaged.itemDoubleClicked.connect(lambda it: rw.stage([it.data(Qt.UserRole)]))
        self.staged.itemDoubleClicked.connect(lambda it: rw.unstage([it.data(Qt.UserRole)]))
        self.unstaged.itemSelectionChanged.connect(lambda: self._sel_changed(self.unstaged))
        self.staged.itemSelectionChanged.connect(lambda: self._sel_changed(self.staged))
        self.unstaged.customContextMenuRequested.connect(lambda p: self._menu(self.unstaged, p, False))
        self.staged.customContextMenuRequested.connect(lambda p: self._menu(self.staged, p, True))
        QShortcut(QKeySequence("Ctrl+S"), self, lambda: rw.stage(self.unstaged.selected()))
        QShortcut(QKeySequence("Ctrl+U"), self, lambda: rw.unstage(self.staged.selected()))

    def _build_commit_box(self) -> QWidget:
        w3 = QFrame()
        w3.setObjectName("card")
        l3 = QVBoxLayout(w3)
        l3.setContentsMargins(10, 8, 10, 10)
        self.recent = QComboBox()
        self.recent.setMinimumWidth(160)
        self.recent.setMaximumWidth(300)
        self.recent.activated.connect(self._use_recent)
        h3 = QHBoxLayout()
        lbl = QLabel(t("work.message"))
        lbl.setObjectName("section")
        h3.addWidget(lbl, 1)
        self.counter = QLabel("")
        self.counter.setObjectName("muted")
        h3.addWidget(self.counter)
        h3.addWidget(self.recent)
        l3.addLayout(h3)
        self.msg = QPlainTextEdit()
        self.msg.setPlaceholderText(t("work.message_hint"))
        self.msg.textChanged.connect(self._count)
        l3.addWidget(self.msg, 1)
        opts = QHBoxLayout()
        self.amend = QCheckBox(t("work.amend"))
        self.signoff = QCheckBox("Sign-off")
        self.noverify = QCheckBox(t("work.no_verify"))
        for c in (self.amend, self.signoff, self.noverify):
            opts.addWidget(c)
        opts.addStretch(1)
        l3.addLayout(opts)
        btns = QHBoxLayout()
        self.btn_commit = QPushButton("✔  " + t("work.commit"))
        self.btn_commit.setObjectName("primary")
        self.btn_commit.setMinimumHeight(36)
        self.btn_commit_push = QPushButton("⇪  " + t("work.commit_push"))
        self.btn_commit_push.setMinimumHeight(36)
        btns.addWidget(self.btn_commit, 2)
        btns.addWidget(self.btn_commit_push, 1)
        l3.addLayout(btns)
        self.btn_commit.clicked.connect(lambda: self.rw.commit(push=False))
        self.btn_commit_push.clicked.connect(lambda: self.rw.commit(push=True))
        self.amend.toggled.connect(self._amend_toggled)
        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(seq), self.msg, lambda: self.rw.commit(push=False))
        QShortcut(QKeySequence("Ctrl+Shift+Return"), self.msg, lambda: self.rw.commit(push=True))
        return w3

    def _count(self):
        first = self.msg.toPlainText().split("\n", 1)[0]
        n = len(first)
        color = theme.C["danger"] if n > 72 else (theme.C["warn"] if n > 50 else theme.C["muted"])
        self.counter.setText(f"<span style='color:{color}'>{n}</span>" if n else "")

    def _use_recent(self, idx: int):
        if idx > 0:
            self.msg.setPlainText(self.recent.itemText(idx))
        self.recent.setCurrentIndex(0)

    def _amend_toggled(self, on: bool):
        if on and not self.msg.toPlainText().strip():
            self.msg.setPlainText(self.rw.repo.last_message())
        self.btn_commit.setText("✔  " + (t("work.amend_commit") if on else t("work.commit")))

    def set_recent(self, msgs: list[str]):
        self.recent.blockSignals(True)
        self.recent.clear()
        self.recent.addItem(t("work.recent"))
        self.recent.addItems(msgs)
        self.recent.blockSignals(False)

    def _sel_changed(self, lst: FileList):
        if lst.selectedItems():
            other = self.staged if lst is self.unstaged else self.unstaged
            other.blockSignals(True)
            other.clearSelection()
            other.blockSignals(False)
            self.active = lst
        self.show_current()

    def show_current(self):
        lst = self.active
        items = lst.selectedItems() if lst else []
        if not items:
            self.diff.clear(t("work.pick_file"))
            return
        fc: FileChange = items[0].data(Qt.UserRole)
        staged = lst is self.staged
        repo = self.rw.repo
        if fc.conflicted and not staged:
            try:
                with open(os.path.join(repo.path, fc.path), "rb") as f:
                    text = f.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            except OSError as e:
                text = str(e)
            self.diff.set_diff(b"", "readonly", "⚠ " + t("work.conflict_title", path=fc.path),
                               t("work.conflict_hint") + "\n\n" + text)
            return
        data = repo.diff_file(fc, staged, self.diff.context, self.diff.ignore_ws)
        mode = "readonly" if fc.untracked else ("staged" if staged else "unstaged")
        self.diff.set_diff(data, mode, (t("work.staged_prefix") if staged else t("work.unstaged_prefix")) + fc.path)

    def _apply_patch(self, patch: bytes, cached: bool, reverse: bool, discard: bool):
        if discard and QMessageBox.question(self, t("work.discard"), t("work.discard_confirm_lines")) \
                != QMessageBox.Yes:
            return
        try:
            self.rw.repo.apply_patch(patch, cached, reverse)
        except GitError as e:
            QMessageBox.warning(self, t("err.patch_failed"), str(e))
        self.rw.refresh()

    def fill(self, changes: list[FileChange]):
        unstaged = [c for c in changes if c.unstaged]
        staged = [c for c in changes if c.staged]
        conflicts = sum(1 for c in changes if c.conflicted)
        self.unstaged.fill(unstaged, False)
        self.staged.fill(staged, True)
        self.lbl_unstaged.setText(t("work.unstaged") + f"  ({len(unstaged)})" +
                                  (f"   ⚠ {t('st.conflict')} {conflicts}" if conflicts else ""))
        self.lbl_staged.setText(t("work.staged") + f"  ({len(staged)})")
        if self.active and not self.active.selectedItems():
            self.active = None
        self.show_current()

    def _menu(self, lst: FileList, pos, staged: bool):
        sel = lst.selected()
        if not sel:
            return
        rw = self.rw
        m = QMenu(self)
        conflicts = [c for c in sel if c.conflicted]
        if conflicts:
            m.addAction(t("work.use_ours"), lambda: rw.resolve(conflicts, "ours"))
            m.addAction(t("work.use_theirs"), lambda: rw.resolve(conflicts, "theirs"))
            m.addAction(t("work.mark_resolved"), lambda: rw.mark_resolved(conflicts))
            m.addAction(t("work.mergetool"), lambda: rw.mergetool(conflicts[0]))
            m.addSeparator()
        if staged:
            m.addAction(t("work.unstage"), lambda: rw.unstage(sel))
        else:
            m.addAction(t("work.stage"), lambda: rw.stage(sel))
            m.addAction(t("work.discard"), lambda: rw.discard(sel))
            m.addAction(t("work.stash_files"), lambda: rw.stash_files(sel))
        m.addSeparator()
        fc = sel[0]
        full = os.path.join(rw.repo.path, fc.path)
        m.addAction(t("file.open_editor"), lambda: rw.open_in_editor(full))
        m.addAction(t("file.open"), lambda: open_path(full) if os.path.exists(full) else None)
        m.addAction(t("file.reveal"), lambda: reveal_in_explorer(full))
        m.addAction(t("file.copy_path"), lambda: QApplication.clipboard().setText("\n".join(c.path for c in sel)))
        if not fc.untracked:
            m.addAction(t("file.history"), lambda: rw.file_history(fc.path))
            m.addAction(t("file.blame"), lambda: rw.blame(fc.path))
        else:
            m.addSeparator()
            ig = m.addMenu(t("file.ignore"))
            ig.addAction(t("file.ignore_file", p=fc.path), lambda: rw.ignore("/" + fc.path))
            ext = os.path.splitext(fc.path)[1]
            if ext:
                ig.addAction(t("file.ignore_ext", p="*" + ext), lambda: rw.ignore("*" + ext))
            d = os.path.dirname(fc.path)
            if d:
                ig.addAction(t("file.ignore_dir", p=d + "/"), lambda: rw.ignore("/" + d + "/"))
        m.exec(lst.mapToGlobal(pos))
