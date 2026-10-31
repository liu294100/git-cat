"""Compare two refs: commits on each side and the combined diff."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QListWidgetItem, QSplitter, QVBoxLayout, QWidget

from ...common.i18n import t
from .. import theme
from ..display import STATUS_COLOR
from ..widgets.diff_view import DiffView

if TYPE_CHECKING:
    from ..repo.view import RepoView


class CompareDialog(QDialog):
    """Compare two refs: commits on each side and the combined diff."""

    def __init__(self, rw: "RepoView", a: str, b: str):
        super().__init__(rw)
        self.rw, self.a, self.b = rw, a, b
        self.setWindowTitle(t("cmp.title", a=a[:20], b=b[:20]))
        self.resize(1300, 820)
        lay = QVBoxLayout(self)
        repo = rw.repo
        ahead = repo.log(rev_range=f"{a}..{b}", max_count=500)
        behind = repo.log(rev_range=f"{b}..{a}", max_count=500)
        add, rem = repo.numstat(a, b)
        head = QLabel(t("cmp.summary", a=a[:20], b=b[:20], ahead=len(ahead), behind=len(behind)) +
                      f"   <span style='color:{theme.C['ok']}'>+{add}</span> "
                      f"<span style='color:{theme.C['danger']}'>−{rem}</span>")
        head.setStyleSheet("font-size: 14px; font-weight: 600;")
        lay.addWidget(head)
        split = QSplitter(Qt.Horizontal)
        lay.addWidget(split, 1)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel(t("cmp.only_in", ref=b[:30])))
        la = QListWidget()
        for c in ahead:
            la.addItem(f"{c.short}  {c.subject}")
        ll.addWidget(la, 1)
        ll.addWidget(QLabel(t("cmp.only_in", ref=a[:30])))
        lb = QListWidget()
        for c in behind:
            lb.addItem(f"{c.short}  {c.subject}")
        ll.addWidget(lb, 1)
        ll.addWidget(QLabel(t("cmp.files")))
        self.files = QListWidget()
        for fc in repo.range_files(a, b):
            it = QListWidgetItem(f"{fc.x}   {fc.path}")
            it.setForeground(QColor(STATUS_COLOR.get(fc.x, theme.C["text"])))
            it.setData(Qt.UserRole, fc)
            self.files.addItem(it)
        ll.addWidget(self.files, 2)
        split.addWidget(left)
        self.diff = DiffView()
        split.addWidget(self.diff)
        split.setSizes([420, 880])
        self.files.currentItemChanged.connect(lambda *_: self._show())
        self.diff.optionsChanged.connect(self._show)
        if self.files.count():
            self.files.setCurrentRow(0)

    def _show(self):
        it = self.files.currentItem()
        if it:
            fc = it.data(Qt.UserRole)
            self.diff.set_diff(self.rw.repo.range_diff(self.a, self.b, fc, self.diff.context, self.diff.ignore_ws),
                               "readonly", fc.path)
