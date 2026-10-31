"""Small reusable widgets: file list, section header, compact button, bar chart."""
from __future__ import annotations

import os

from PySide6.QtCore import QItemSelectionModel, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
                               QWidget)

from ...core.models import FileChange
from .. import theme
from ..display import STATUS_COLOR, status_letter, status_text


class FileList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setUniformItemSizes(True)
        self._filter = ""

    def fill(self, changes: list[FileChange], staged: bool):
        keep = {i.data(Qt.UserRole).path for i in self.selectedItems()}
        self.blockSignals(True)
        self.clear()
        for fc in changes:
            letter = status_letter(fc, staged)
            label = f"{fc.orig_path} → {fc.path}" if (staged and fc.orig_path) else fc.path
            name = os.path.basename(fc.path)
            folder = os.path.dirname(label)
            it = QListWidgetItem(f"{letter}   {name}" + (f"    {folder}" if folder else ""))
            it.setData(Qt.UserRole, fc)
            it.setForeground(QColor(STATUS_COLOR.get(letter, theme.C["text"])))
            it.setToolTip(f"{status_text(letter)}: {label}")
            self.addItem(it)
            it.setHidden(bool(self._filter) and self._filter not in fc.path.lower())
            if fc.path in keep:
                it.setSelected(True)
                self.setCurrentItem(it, QItemSelectionModel.NoUpdate)
        self.blockSignals(False)

    def set_filter(self, text: str):
        self._filter = text.lower().strip()
        for i in range(self.count()):
            it = self.item(i)
            it.setHidden(bool(self._filter) and self._filter not in it.data(Qt.UserRole).path.lower())

    def selected(self) -> list[FileChange]:
        return [i.data(Qt.UserRole) for i in self.selectedItems()]

    def all_visible(self) -> list[FileChange]:
        return [self.item(i).data(Qt.UserRole) for i in range(self.count()) if not self.item(i).isHidden()]


def header(title: str, *buttons: QPushButton) -> tuple[QHBoxLayout, QLabel]:
    h = QHBoxLayout()
    lbl = QLabel(title)
    lbl.setObjectName("section")
    h.addWidget(lbl, 1)
    for b in buttons:
        h.addWidget(b)
    return h, lbl


def small_button(text: str, tip: str = "", obj: str = "") -> QPushButton:
    b = QPushButton(text)
    b.setToolTip(tip or text)
    if obj:
        b.setObjectName(obj)
    b.setStyleSheet("padding: 4px 10px;")
    return b


class BarChart(QWidget):
    def __init__(self, data: list[tuple[str, int]]):
        super().__init__()
        self.data = data
        self.setMinimumHeight(max(60, 30 * len(data)))

    def paintEvent(self, _):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        mx = max(v for _, v in self.data) or 1
        w = self.width()
        label_w = min(260, w // 3)
        for i, (name, v) in enumerate(self.data):
            y = i * 30 + 4
            p.setPen(theme.color("text"))
            p.drawText(QRectF(0, y, label_w - 8, 22), Qt.AlignRight | Qt.AlignVCenter,
                       p.fontMetrics().elidedText(name, Qt.ElideRight, label_w - 8))
            bw = max(4, (w - label_w - 70) * v / mx)
            r = QRectF(label_w, y + 3, bw, 16)
            g = QLinearGradient(r.topLeft(), r.topRight())
            g.setColorAt(0, theme.color("accent"))
            g.setColorAt(1, theme.color("accent2"))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(r, 8, 8)
            p.setPen(theme.color("muted"))
            p.drawText(QRectF(label_w + bw + 8, y, 60, 22), Qt.AlignLeft | Qt.AlignVCenter, str(v))
        p.end()
