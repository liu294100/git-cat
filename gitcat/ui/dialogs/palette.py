"""Ctrl+Shift+P command palette."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from ...common.i18n import t
from ...common.fuzzy import fuzzy_score


class CommandPalette(QDialog):
    def __init__(self, parent, items: list[tuple[str, Callable[[], None]]]):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("palette")
        self.items = items
        self.resize(680, 460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        self.input = QLineEdit()
        self.input.setPlaceholderText("⌘  " + t("palette.hint"))
        self.input.setStyleSheet("font-size: 15px; padding: 10px;")
        self.list = QListWidget()
        lay.addWidget(self.input)
        lay.addWidget(self.list)
        self.input.textChanged.connect(self._filter)
        self.input.returnPressed.connect(self._exec)
        self.list.itemActivated.connect(lambda _: self._exec())
        self.input.installEventFilter(self)
        self._filter("")
        if parent:
            g = parent.geometry()
            self.move(g.x() + (g.width() - self.width()) // 2, g.y() + 90)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Up, Qt.Key_Down):
            r = self.list.currentRow() + (1 if ev.key() == Qt.Key_Down else -1)
            if 0 <= r < self.list.count():
                self.list.setCurrentRow(r)
            return True
        return super().eventFilter(obj, ev)

    def _filter(self, q: str):
        self.list.clear()
        scored = [(fuzzy_score(q, name), i) for i, (name, _) in enumerate(self.items)]
        scored = sorted([s for s in scored if s[0] >= 0], key=lambda s: -s[0])[:200]
        for _, i in scored:
            it = QListWidgetItem(self.items[i][0])
            it.setData(Qt.UserRole, i)
            self.list.addItem(it)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _exec(self):
        it = self.list.currentItem()
        if not it:
            return
        fn = self.items[it.data(Qt.UserRole)][1]
        self.accept()
        fn()
