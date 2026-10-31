"""Interactive rebase planner."""
from __future__ import annotations


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
                               QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ...common.i18n import t
from ...core.models import Commit


class InteractiveRebaseDialog(QDialog):
    ACTIONS = ["pick", "reword", "squash", "fixup", "drop"]

    def __init__(self, parent, commits: list[Commit], base_label: str):
        super().__init__(parent)
        self.setWindowTitle(t("irebase.title"))
        self.resize(940, 580)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lb = QLabel(t("irebase.hint", base=base_label))
        lb.setWordWrap(True)
        lay.addWidget(lb)
        self.table = QTableWidget(len(commits), 3)
        self.table.setHorizontalHeaderLabels([t("irebase.action"), t("hist.col.sha"), t("irebase.message")])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 220)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.commits = list(commits)
        for i, c in enumerate(self.commits):
            self._fill_row(i, c, "pick", c.subject)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        up = QPushButton("↑ " + t("irebase.up"))
        down = QPushButton("↓ " + t("irebase.down"))
        up.clicked.connect(lambda: self._move(-1))
        down.clicked.connect(lambda: self._move(1))
        row.addWidget(up)
        row.addWidget(down)
        row.addStretch(1)
        lay.addLayout(row)
        self.err = QLabel("")
        self.err.setObjectName("error")
        lay.addWidget(self.err)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(t("irebase.start"))
        bb.button(QDialogButtonBox.Ok).setObjectName("primary")
        bb.button(QDialogButtonBox.Cancel).setText(t("common.cancel"))
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _fill_row(self, i: int, c: Commit, action: str, msg: str):
        cb = QComboBox()
        for a in self.ACTIONS:
            cb.addItem(f"{a} · {t('irebase.' + a)}", a)
        cb.setCurrentIndex(self.ACTIONS.index(action))
        self.table.setCellWidget(i, 0, cb)
        it = QTableWidgetItem(c.short)
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(i, 1, it)
        self.table.setItem(i, 2, QTableWidgetItem(msg))

    def _row_state(self, i):
        return self.table.cellWidget(i, 0).currentData(), self.table.item(i, 2).text()

    def _move(self, d: int):
        i = self.table.currentRow()
        j = i + d
        if i < 0 or not (0 <= j < self.table.rowCount()):
            return
        si, sj = self._row_state(i), self._row_state(j)
        self.commits[i], self.commits[j] = self.commits[j], self.commits[i]
        self._fill_row(i, self.commits[i], *sj)
        self._fill_row(j, self.commits[j], *si)
        self.table.selectRow(j)

    def plan(self) -> list[tuple[str, str, str]]:
        res = []
        for i, c in enumerate(self.commits):
            a, msg = self._row_state(i)
            if a == "reword" and msg.strip() == c.subject:
                a = "pick"
            res.append((a, c.sha, msg))
        return res

    def _ok(self):
        p = self.plan()
        first = next((a for a, _, _ in p if a != "drop"), None)
        if first in ("squash", "fixup"):
            self.err.setText(t("irebase.err_first"))
            return
        self.accept()
