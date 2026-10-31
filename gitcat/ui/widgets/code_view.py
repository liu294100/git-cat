"""Read-only code viewer with line numbers, current-line highlight and find (Ctrl+F)."""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QShortcut, QTextCursor, QTextDocument, QTextFormat, \
    QTextOption
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget

from ...common.i18n import t
from ...core.runner import decode
from .. import theme

MAX_VIEW = 4 * 1024 * 1024


class _Gutter(QWidget):
    def __init__(self, ed: "CodeEdit"):
        super().__init__(ed)
        self.ed = ed

    def sizeHint(self) -> QSize:
        return QSize(self.ed.gutter_width(), 0)

    def paintEvent(self, e):
        self.ed.paint_gutter(e)


class CodeEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setWordWrapMode(QTextOption.NoWrap)
        f = QFont("Cascadia Mono")
        if not f.exactMatch():
            f = QFont("Consolas")
        f.setPointSize(10)
        f.setStyleHint(QFont.Monospace)
        self.setFont(f)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.gutter = _Gutter(self)
        self.blockCountChanged.connect(lambda _: self.setViewportMargins(self.gutter_width(), 0, 0, 0))
        self.updateRequest.connect(self._on_update)
        self.cursorPositionChanged.connect(self._highlight)
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def gutter_width(self) -> int:
        return self.fontMetrics().horizontalAdvance("9") * max(4, len(str(self.blockCount())) + 1) + 12

    def _on_update(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, event):
        p = QPainter(self.gutter)
        p.fillRect(event.rect(), theme.color("gutter"))
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        cur = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            h = round(self.blockBoundingRect(block).height())
            n = block.blockNumber()
            p.setPen(theme.color("accent2") if n == cur else theme.color("muted"))
            p.drawText(0, top, self.gutter.width() - 8, h, Qt.AlignRight, str(n + 1))
            top += h
            block = block.next()
        p.end()

    def _highlight(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor(theme.C["hover"]))
        sel.format.setProperty(QTextFormat.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])

    def goto_line(self, line: int):
        block = self.document().findBlockByNumber(max(0, line - 1))
        c = QTextCursor(block)
        self.setTextCursor(c)
        self.centerCursor()


class CodeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 4, 6, 2)
        self.title = QLabel("")
        self.title.setObjectName("diffTitle")
        bar.addWidget(self.title, 1)
        self.info = QLabel("")
        self.info.setObjectName("muted")
        bar.addWidget(self.info)
        self.find = QLineEdit()
        self.find.setPlaceholderText("🔎 " + t("files.find"))
        self.find.setMaximumWidth(240)
        self.find.setClearButtonEnabled(True)
        bar.addWidget(self.find)
        lay.addLayout(bar)
        self.edit = CodeEdit(self)
        lay.addWidget(self.edit, 1)
        self.find.returnPressed.connect(lambda: self._find(False))
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: (self.find.setFocus(), self.find.selectAll()))
        QShortcut(QKeySequence("F3"), self, lambda: self._find(False))
        QShortcut(QKeySequence("Shift+F3"), self, lambda: self._find(True))

    def _find(self, back: bool):
        q = self.find.text()
        if not q:
            return
        flags = QTextDocument.FindBackward if back else QTextDocument.FindFlag(0)
        if not self.edit.find(q, flags):
            c = self.edit.textCursor()
            c.movePosition(QTextCursor.End if back else QTextCursor.Start)
            self.edit.setTextCursor(c)
            self.edit.find(q, flags)

    def show_bytes(self, data: bytes, title: str):
        self.title.setText(title)
        if b"\0" in data[:8000]:
            self.edit.setPlainText(t("diff.binary"))
            self.info.setText(f"{len(data) // 1024} KB")
            return
        text = decode(data[:MAX_VIEW])
        self.edit.setPlainText(text)
        self.info.setText(f"{text.count(chr(10)) + 1} lines · {max(1, len(data) // 1024)} KB" +
                          (" · truncated" if len(data) > MAX_VIEW else ""))

    def clear(self, msg: str = ""):
        self.title.setText("")
        self.info.setText("")
        self.edit.setPlainText(msg)
