"""Side-by-side diff: two synchronised editors with aligned rows, line numbers and intraline highlight."""
from __future__ import annotations

import difflib
from typing import Optional

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextOption
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QSplitter, QWidget

from ...core.diff import ParsedDiff
from ...core.runner import decode
from .. import theme

Row = tuple[str, str, int]  # (kind, text, line number or 0)
MAX_INTRALINE = 600


class _Gutter(QWidget):
    def __init__(self, ed: "SideEdit"):
        super().__init__(ed)
        self.ed = ed

    def sizeHint(self) -> QSize:
        return QSize(self.ed.gutter_width(), 0)

    def paintEvent(self, e):
        self.ed.paint_gutter(e)


class SideEdit(QPlainTextEdit):
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
        self.rows: list[Row] = []
        self.gutter = _Gutter(self)
        self.updateRequest.connect(self._on_update)
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def gutter_width(self) -> int:
        return self.fontMetrics().horizontalAdvance("9") * 6 + 12

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
        w = self.gutter.width()
        while block.isValid() and top <= event.rect().bottom():
            h = round(self.blockBoundingRect(block).height())
            n = block.blockNumber()
            if n < len(self.rows):
                kind, _, num = self.rows[n]
                if kind in ("add", "del"):
                    p.fillRect(w - 3, top, 3, h, theme.color("ok" if kind == "add" else "danger"))
                if num:
                    p.setPen(theme.color("muted"))
                    p.drawText(0, top, w - 8, h, Qt.AlignRight, str(num))
            top += h
            block = block.next()
        p.end()

    def load(self, rows: list[Row]):
        self.clear()
        self.rows = rows
        C = theme.C
        fmts = {}
        for kind, bg, fg in (("ctx", None, C["text"]), ("add", C["add_bg"], C["add_fg"]),
                             ("del", C["del_bg"], C["del_fg"]), ("hunk", C["hunk_bg"], C["hunk_fg"]),
                             ("pad", C["panel"], C["muted"]), ("info", None, C["muted"])):
            bf = QTextBlockFormat()
            if bg:
                bf.setBackground(QBrush(QColor(bg)))
            cf = QTextCharFormat()
            cf.setForeground(QColor(fg))
            fmts[kind] = (bf, cf)
        cur = QTextCursor(self.document())
        cur.beginEditBlock()
        for i, (kind, text, _) in enumerate(rows):
            bf, cf = fmts.get(kind, fmts["ctx"])
            if i == 0:
                cur.setBlockFormat(bf)
                cur.setCharFormat(cf)
            else:
                cur.insertBlock(bf, cf)
            cur.insertText(text, cf)
        cur.endEditBlock()
        self.moveCursor(QTextCursor.Start)
        self.gutter.update()

    def mark(self, row: int, start: int, end: int, fmt: QTextCharFormat):
        block = self.document().findBlockByNumber(row)
        c = QTextCursor(block)
        c.setPosition(block.position() + start)
        c.setPosition(block.position() + min(end, block.length() - 1), QTextCursor.KeepAnchor)
        c.mergeCharFormat(fmt)


def build_rows(pd: ParsedDiff) -> tuple[list[Row], list[Row], list[int]]:
    """Return aligned left/right rows and the indexes of paired changed rows (for intraline marks)."""
    left: list[Row] = []
    right: list[Row] = []
    pairs: list[int] = []
    for h in pd.hunks:
        tail = decode(h.tail).strip()
        left.append(("hunk", f"@@ -{h.old_start}  {tail}", 0))
        right.append(("hunk", f"@@ +{h.new_start}", 0))
        o, n = h.old_start, h.new_start
        dels: list[str] = []
        adds: list[str] = []

        def flush():
            nonlocal o, n
            for i in range(max(len(dels), len(adds))):
                if i < len(dels):
                    left.append(("del", dels[i], o))
                    o += 1
                else:
                    left.append(("pad", "", 0))
                if i < len(adds):
                    right.append(("add", adds[i], n))
                    n += 1
                else:
                    right.append(("pad", "", 0))
                if i < len(dels) and i < len(adds):
                    pairs.append(len(left) - 1)
            dels.clear()
            adds.clear()

        for raw in h.lines:
            c = raw[:1]
            text = decode(raw[1:].rstrip(b"\r"))
            if c == b"-":
                if adds:
                    flush()
                dels.append(text)
            elif c == b"+":
                adds.append(text)
            elif c == b"\\":
                continue
            else:
                flush()
                left.append(("ctx", text, o))
                right.append(("ctx", text, n))
                o += 1
                n += 1
        flush()
    return left, right, pairs


class SideBySideView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Horizontal)
        self.left, self.right = SideEdit(), SideEdit()
        split.addWidget(self.left)
        split.addWidget(self.right)
        lay.addWidget(split)
        self._syncing = False
        for a, b in ((self.left, self.right), (self.right, self.left)):
            a.verticalScrollBar().valueChanged.connect(lambda v, b=b: self._sync(b.verticalScrollBar(), v))
            a.horizontalScrollBar().valueChanged.connect(lambda v, b=b: self._sync(b.horizontalScrollBar(), v))

    def _sync(self, bar, value):
        if self._syncing:
            return
        self._syncing = True
        bar.setValue(value)
        self._syncing = False

    def load(self, pd: ParsedDiff, message: Optional[str] = None):
        if message is not None or not pd.hunks:
            info = [("info", message or "", 0)]
            self.left.load(info)
            self.right.load(info)
            return
        left, right, pairs = build_rows(pd)
        self.left.load(left)
        self.right.load(right)
        if len(left) > 20000:
            return
        add_hl, del_hl = QTextCharFormat(), QTextCharFormat()
        light = theme.CURRENT == "light"
        add_hl.setBackground(QColor("#a7f3c0") if light else QColor(theme.C["ok"]).darker(160))
        del_hl.setBackground(QColor("#fecaca") if light else QColor(theme.C["danger"]).darker(170))
        for i in pairs:
            old, new = left[i][1], right[i][1]
            if len(old) > MAX_INTRALINE or len(new) > MAX_INTRALINE:
                continue
            sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
            if sm.ratio() < 0.35:
                continue
            for tag, a1, a2, b1, b2 in sm.get_opcodes():
                if tag == "equal":
                    continue
                if a2 > a1:
                    self.left.mark(i, a1, a2, del_hl)
                if b2 > b1:
                    self.right.mark(i, b1, b2, add_hl)
