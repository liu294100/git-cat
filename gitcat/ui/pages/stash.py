"""Stash browser page."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QPushButton, QSplitter, QVBoxLayout,
                               QWidget)

from ...common.i18n import t
from .. import theme
from ..display import STATUS_COLOR
from ..widgets.common import header, small_button
from ..widgets.diff_view import DiffView

if TYPE_CHECKING:
    from ..repo.view import RepoView


class StashPage(QWidget):
    def __init__(self, rw: "RepoView"):
        super().__init__()
        self.rw = rw
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        split = QSplitter(Qt.Horizontal)
        lay.addWidget(split)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        b_new = small_button("＋ " + t("stash.title"), obj="primary")
        h, _ = header(t("stash.list"), b_new)
        ll.addLayout(h)
        self.list = QListWidget()
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        ll.addWidget(self.list, 2)
        row = QHBoxLayout()
        self.b_apply = QPushButton(t("stash.apply"))
        self.b_pop = QPushButton(t("stash.pop"))
        self.b_drop = QPushButton(t("stash.drop"))
        self.b_drop.setObjectName("danger")
        for b in (self.b_apply, self.b_pop, self.b_drop):
            row.addWidget(b)
        ll.addLayout(row)
        self.files = QListWidget()
        ll.addWidget(self.files, 3)
        split.addWidget(left)
        self.diff = DiffView()
        split.addWidget(self.diff)
        split.setSizes([420, 900])
        b_new.clicked.connect(rw.stash)
        self.b_apply.clicked.connect(lambda: self._ref() and rw.stash_apply(self._ref(), False))
        self.b_pop.clicked.connect(lambda: self._ref() and rw.stash_apply(self._ref(), True))
        self.b_drop.clicked.connect(lambda: self._ref() and rw.stash_drop(self._ref()))
        self.list.currentItemChanged.connect(lambda *_: self._show())
        self.files.currentItemChanged.connect(lambda *_: self._show_file())
        self.diff.optionsChanged.connect(self._show_file)
        self.list.customContextMenuRequested.connect(self._menu)

    def _ref(self) -> str:
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else ""

    def fill(self, stashes: list[tuple[str, str, str]]):
        cur = self._ref()
        self.list.blockSignals(True)
        self.list.clear()
        for ref, msg, when in stashes:
            it = QListWidgetItem(f"📦  {msg}\n      {ref} · {when}")
            it.setData(Qt.UserRole, ref)
            self.list.addItem(it)
            if ref == cur:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if not stashes:
            self.files.clear()
            self.diff.clear(t("stash.empty"))
        elif not self.list.currentItem():
            self.list.setCurrentRow(0)
        else:
            self._show()

    def _show(self):
        ref = self._ref()
        self.files.clear()
        if not ref:
            return
        for fc in self.rw.repo.stash_files(ref):
            it = QListWidgetItem(f"{fc.x}   {fc.path}")
            it.setForeground(QColor(STATUS_COLOR.get(fc.x, theme.C["text"])))
            it.setData(Qt.UserRole, fc)
            self.files.addItem(it)
        if self.files.count():
            self.files.setCurrentRow(0)

    def _show_file(self):
        it = self.files.currentItem()
        ref = self._ref()
        if not it or not ref:
            return
        fc = it.data(Qt.UserRole)
        self.diff.set_diff(self.rw.repo.stash_file_diff(ref, fc, self.diff.context, self.diff.ignore_ws),
                           "readonly", f"{ref}: {fc.path}")

    def _menu(self, pos):
        ref = self._ref()
        if not ref:
            return
        m = QMenu(self)
        m.addAction(t("stash.apply"), lambda: self.rw.stash_apply(ref, False))
        m.addAction(t("stash.apply_index"), lambda: self.rw.stash_apply(ref, False, index=True))
        m.addAction(t("stash.pop"), lambda: self.rw.stash_apply(ref, True))
        m.addAction(t("stash.to_branch"), lambda: self.rw.stash_branch(ref))
        m.addSeparator()
        m.addAction(t("stash.drop"), lambda: self.rw.stash_drop(ref))
        m.exec(self.list.mapToGlobal(pos))
