"""Base form dialog with validation and the editable combo helper."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout

from ...common.i18n import t
from .. import theme


class FormDialog(QDialog):
    def __init__(self, parent, title: str, ok_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(540)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(22, 18, 22, 18)
        self.outer.setSpacing(12)
        head = QLabel(title)
        head.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {theme.C['text']};")
        self.outer.addWidget(head)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignRight)
        self.form.setHorizontalSpacing(14)
        self.form.setVerticalSpacing(10)
        self.outer.addLayout(self.form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok = self.buttons.button(QDialogButtonBox.Ok)
        ok.setText(ok_text or t("common.ok"))
        ok.setObjectName("primary")
        self.buttons.button(QDialogButtonBox.Cancel).setText(t("common.cancel"))
        self.buttons.accepted.connect(self._ok)
        self.buttons.rejected.connect(self.reject)
        self._validators: list[Callable[[], Optional[str]]] = []
        self.err = QLabel("")
        self.err.setObjectName("error")

    def finish(self):
        self.outer.addWidget(self.err)
        self.outer.addWidget(self.buttons)

    def validate(self, fn: Callable[[], Optional[str]]):
        self._validators.append(fn)

    def _ok(self):
        for v in self._validators:
            msg = v()
            if msg:
                self.err.setText(msg)
                return
        self.accept()


def editable_combo(items: list[str], current: str = "") -> QComboBox:
    cb = QComboBox()
    cb.setEditable(True)
    cb.addItems(items)
    if current:
        cb.setCurrentText(current)
    return cb
