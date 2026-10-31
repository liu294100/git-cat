"""Read-only viewers: table picker (reflog, file history), text and blame."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from ...common.i18n import t
from ..display import avatar_color


class ListPickDialog(QDialog):
    """Generic "table + action buttons" dialog (reflog, worktrees...)."""

    def __init__(self, parent, title: str, headers: list[str], rows: list[list[str]],
                 actions: list[tuple[str, Callable[[int], None]]], stretch: int = -2):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(960, 580)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(t("common.filter"))
        self.filter.textChanged.connect(self._filter)
        lay.addWidget(self.filter)
        self.table = QTableWidget(len(rows), len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(len(headers) + stretch if stretch < 0 else stretch,
                                                           QHeaderView.Stretch)
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                self.table.setItem(i, j, QTableWidgetItem(v))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(len(headers) + stretch if stretch < 0 else stretch,
                                                           QHeaderView.Stretch)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        for text, fn in actions:
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, f=fn: self._run(f))
            row.addWidget(b)
        close = QPushButton(t("common.close"))
        close.clicked.connect(self.reject)
        row.addWidget(close)
        lay.addLayout(row)
        if actions:
            self.table.doubleClicked.connect(lambda _: self._run(actions[0][1]))

    def _filter(self, q: str):
        q = q.lower()
        for i in range(self.table.rowCount()):
            text = " ".join(self.table.item(i, j).text() for j in range(self.table.columnCount())
                            if self.table.item(i, j))
            self.table.setRowHidden(i, bool(q) and q not in text.lower())

    def _run(self, fn):
        r = self.table.currentRow()
        if r >= 0:
            fn(r)


class TextDialog(QDialog):
    def __init__(self, parent, title: str, text: str, mono: bool = True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 650)
        lay = QVBoxLayout(self)
        ed = QPlainTextEdit(text)
        ed.setReadOnly(True)
        ed.setLineWrapMode(QPlainTextEdit.NoWrap)
        if mono:
            ed.setFont(QFont("Consolas", 10))
        lay.addWidget(ed)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(t("common.close"))
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class BlameDialog(QDialog):
    def __init__(self, parent, path: str, rows: list[tuple[str, str, str, int, str]],
                 on_commit: Callable[[str], None]):
        super().__init__(parent)
        self.setWindowTitle(t("blame.title", path=path))
        self.resize(1200, 760)
        lay = QVBoxLayout(self)
        tbl = QTableWidget(len(rows), 5)
        tbl.setHorizontalHeaderLabels([t("hist.col.sha"), t("hist.col.author"), t("hist.col.date"), "#",
                                       t("blame.code")])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setShowGrid(False)
        tbl.verticalHeader().setDefaultSectionSize(20)
        mono = QFont("Consolas", 10)
        prev = ""
        for i, (sha, author, date, ln, text) in enumerate(rows):
            same = sha == prev
            prev = sha
            vals = ["" if same else sha[:8], "" if same else author, "" if same else date, str(ln), text]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if j in (0, 3, 4):
                    it.setFont(mono)
                if j == 0:
                    it.setData(Qt.UserRole, sha)
                    it.setForeground(QColor(avatar_color(sha)))
                if j == 1:
                    it.setForeground(QColor(avatar_color(author)))
                tbl.setItem(i, j, it)
        tbl.resizeColumnsToContents()
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        lay.addWidget(tbl)
        hint = QLabel(t("blame.hint"))
        hint.setObjectName("muted")
        lay.addWidget(hint)

        def jump(idx):
            sha = rows[idx.row()][0]
            self.accept()
            on_commit(sha)
        tbl.doubleClicked.connect(jump)
