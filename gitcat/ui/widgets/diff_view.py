"""Coloured diff widget with line-number gutter, intraline highlight and hunk/line staging."""
from __future__ import annotations

import difflib
from typing import Callable, Optional

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QTextBlockFormat, QTextCharFormat, QTextCursor,
                           QTextOption)
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QMenu, QPlainTextEdit, QPushButton, QSpinBox,
                               QStackedWidget, QVBoxLayout, QWidget)

from ...common.i18n import t
from ...core.diff import HUNK_RE, ParsedDiff, build_patch, parse_diff
from ...core.runner import decode
from .. import theme
from .side_by_side import SideBySideView


MAX_DISPLAY = 3 * 1024 * 1024


MAX_INTRALINE = 600


class _Gutter(QWidget):
    def __init__(self, editor: "DiffEdit"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_gutter(event)


class DiffEdit(QPlainTextEdit):
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
        self.rows: list[tuple] = []  # (kind, hunk, line, old_no, new_no)
        self.gutter = _Gutter(self)
        self.blockCountChanged.connect(lambda _: self._update_margin())
        self.updateRequest.connect(self._on_update)
        self._update_margin()

    def gutter_width(self) -> int:
        return self.fontMetrics().horizontalAdvance("9") * 12 + 14

    def _update_margin(self):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

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
        fm = self.fontMetrics()
        half = fm.horizontalAdvance("9") * 6
        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        add_c, del_c, mute = theme.color("ok"), theme.color("danger"), theme.color("muted")
        while block.isValid() and top <= event.rect().bottom():
            h = round(self.blockBoundingRect(block).height())
            n = block.blockNumber()
            if n < len(self.rows):
                kind, _, _, o, nw = self.rows[n]
                if kind == "add":
                    p.fillRect(self.gutter.width() - 3, top, 3, h, add_c)
                elif kind == "del":
                    p.fillRect(self.gutter.width() - 3, top, 3, h, del_c)
                p.setPen(mute)
                if o:
                    p.drawText(0, top, half - 4, h, Qt.AlignRight, str(o))
                if nw:
                    p.drawText(half, top, half - 4, h, Qt.AlignRight, str(nw))
            top += h
            block = block.next()
        p.end()

    def load(self, data: bytes, pd: ParsedDiff, message: str = ""):
        self.clear()
        self.rows = []
        cur = QTextCursor(self.document())
        cur.beginEditBlock()
        C = theme.C
        fmts = {}
        for kind, bg, fg in (("ctx", None, C["text"]), ("add", C["add_bg"], C["add_fg"]),
                             ("del", C["del_bg"], C["del_fg"]), ("hunk", C["hunk_bg"], C["hunk_fg"]),
                             ("head", C["panel2"], C["head_fg"]), ("info", None, C["muted"])):
            bf = QTextBlockFormat()
            if bg:
                bf.setBackground(QBrush(QColor(bg)))
            cf = QTextCharFormat()
            cf.setForeground(QColor(fg))
            if kind == "head":
                cf.setFontWeight(QFont.Bold)
            fmts[kind] = (bf, cf)
        first = [True]

        def add(kind, text, hi=-1, li=-1, o=0, n=0):
            bf, cf = fmts[kind]
            if first[0]:
                cur.setBlockFormat(bf)
                cur.setCharFormat(cf)
                first[0] = False
            else:
                cur.insertBlock(bf, cf)
            cur.insertText(text, cf)
            self.rows.append((kind, hi, li, o, n))

        if message:
            add("info", message)
        elif len(data) > MAX_DISPLAY:
            add("info", t("diff.too_large", kb=len(data) // 1024))
        elif pd.binary and not pd.hunks:
            add("info", t("diff.binary"))
        elif pd.files > 1:
            o = n = 0
            for raw in data.split(b"\n"):
                tx = decode(raw.rstrip(b"\r"))
                m = HUNK_RE.match(raw)
                if m:
                    o, n = int(m.group(1)), int(m.group(3))
                    add("hunk", tx)
                elif raw.startswith(b"diff --git"):
                    add("head", "  " + tx[11:].split(" b/")[-1])
                elif raw.startswith((b"index ", b"--- ", b"+++ ", b"new file", b"deleted file", b"similarity",
                                     b"rename ", b"old mode", b"new mode")):
                    continue
                elif raw.startswith(b"+"):
                    add("add", tx, o=0, n=n)
                    n += 1
                elif raw.startswith(b"-"):
                    add("del", tx, o=o)
                    o += 1
                elif raw.startswith(b" "):
                    add("ctx", tx, o=o, n=n)
                    o += 1
                    n += 1
                elif tx:
                    add("info", tx)
        else:
            for raw in pd.header:
                tx = decode(raw.rstrip(b"\r"))
                if tx.startswith(("rename", "new file", "deleted file", "old mode", "new mode", "similarity")):
                    add("info", tx)
            if not pd.hunks and not self.rows:
                add("info", t("diff.no_content"))
            for hi, h in enumerate(pd.hunks):
                add("hunk", decode(b"@@ -%d +%d @@" % (h.old_start, h.new_start) + h.tail), hi)
                o, n = h.old_start, h.new_start
                for li, raw in enumerate(h.lines):
                    tx = decode(raw.rstrip(b"\r"))
                    c = raw[:1]
                    if c == b"+":
                        add("add", tx, hi, li, 0, n)
                        n += 1
                    elif c == b"-":
                        add("del", tx, hi, li, o, 0)
                        o += 1
                    elif c == b"\\":
                        add("info", tx, hi, li)
                    else:
                        add("ctx", tx, hi, li, o, n)
                        o += 1
                        n += 1
        cur.endEditBlock()
        if not message and len(self.rows) < 20000:
            self._intraline()
        self.moveCursor(QTextCursor.Start)
        self.gutter.update()

    def _intraline(self):
        """Highlight the changed characters inside paired -/+ line runs."""
        doc = self.document()
        add_hl, del_hl = QTextCharFormat(), QTextCharFormat()
        add_hl.setBackground(QColor(theme.C["ok"]).darker(160 if theme.CURRENT != "light" else 100))
        del_hl.setBackground(QColor(theme.C["danger"]).darker(170 if theme.CURRENT != "light" else 100))
        if theme.CURRENT == "light":
            add_hl.setBackground(QColor("#a7f3c0"))
            del_hl.setBackground(QColor("#fecaca"))
        i, total = 0, len(self.rows)
        while i < total:
            if self.rows[i][0] != "del":
                i += 1
                continue
            ds = i
            while i < total and self.rows[i][0] == "del":
                i += 1
            as_ = i
            while i < total and self.rows[i][0] == "add":
                i += 1
            dels, adds = list(range(ds, as_)), list(range(as_, i))
            for d, a in zip(dels, adds):
                bd, ba = doc.findBlockByNumber(d), doc.findBlockByNumber(a)
                old, new = bd.text()[1:], ba.text()[1:]
                if len(old) > MAX_INTRALINE or len(new) > MAX_INTRALINE:
                    continue
                sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
                if sm.ratio() < 0.35:
                    continue
                for tag, a1, a2, b1, b2 in sm.get_opcodes():
                    if tag == "equal":
                        continue
                    if a2 > a1:
                        self._mark(bd, a1 + 1, a2 + 1, del_hl)
                    if b2 > b1:
                        self._mark(ba, b1 + 1, b2 + 1, add_hl)

    def _mark(self, block, start: int, end: int, fmt: QTextCharFormat):
        c = QTextCursor(block)
        c.setPosition(block.position() + start)
        c.setPosition(block.position() + end, QTextCursor.KeepAnchor)
        c.mergeCharFormat(fmt)

    def selected_blocks(self) -> tuple[int, int]:
        c = self.textCursor()
        doc = self.document()
        a = doc.findBlock(c.selectionStart()).blockNumber()
        b = doc.findBlock(c.selectionEnd()).blockNumber()
        if c.hasSelection() and b > a and doc.findBlock(c.selectionEnd()).position() == c.selectionEnd():
            b -= 1
        return a, b


class DiffView(QWidget):
    """mode: 'unstaged' | 'staged' | 'readonly'. applier(patch, cached, reverse, discard)."""
    optionsChanged = Signal()

    def __init__(self, parent=None, interactive: bool = False):
        super().__init__(parent)
        self.mode = "readonly"
        self.pd = ParsedDiff()
        self.applier: Optional[Callable[[bytes, bool, bool, bool], None]] = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 4, 6, 2)
        self.title = QLabel("")
        self.title.setObjectName("diffTitle")
        bar.addWidget(self.title, 1)
        self.stat = QLabel("")
        bar.addWidget(self.stat)
        self.btn_hunk = QPushButton(t("diff.stage_hunk"))
        self.btn_lines = QPushButton(t("diff.stage_lines"))
        self.btn_discard = QPushButton(t("diff.discard_lines"))
        self.btn_discard.setObjectName("danger")
        for b in (self.btn_hunk, self.btn_lines, self.btn_discard):
            b.setVisible(interactive)
            bar.addWidget(b)
        bar.addWidget(QLabel(t("diff.context")))
        self.ctx = QSpinBox()
        self.ctx.setRange(0, 999)
        self.ctx.setValue(3)
        bar.addWidget(self.ctx)
        self.ws = QCheckBox(t("diff.ignore_ws"))
        bar.addWidget(self.ws)
        self.sbs_box = QCheckBox(t("diff.side_by_side"))
        self.sbs_box.setChecked(DiffView.side_by_side_default)
        bar.addWidget(self.sbs_box)
        lay.addLayout(bar)
        self.stack = QStackedWidget()
        self.edit = DiffEdit(self)
        self.sbs = SideBySideView(self)
        self.stack.addWidget(self.edit)
        self.stack.addWidget(self.sbs)
        lay.addWidget(self.stack, 1)
        self._data, self._message = b"", ""
        self.sbs_box.toggled.connect(self._toggle_sbs)
        self.ctx.valueChanged.connect(lambda _: self.optionsChanged.emit())
        self.ws.toggled.connect(lambda _: self.optionsChanged.emit())
        self.btn_hunk.clicked.connect(lambda: self._apply(whole_hunk=True, discard=False))
        self.btn_lines.clicked.connect(lambda: self._apply(whole_hunk=False, discard=False))
        self.btn_discard.clicked.connect(lambda: self._apply(whole_hunk=False, discard=True))
        self.edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.edit.customContextMenuRequested.connect(self._menu)
        self._update_buttons()

    @property
    def context(self) -> int:
        return self.ctx.value()

    @property
    def ignore_ws(self) -> bool:
        return self.ws.isChecked()

    def set_diff(self, data: bytes, mode: str = "readonly", title: str = "", message: str = ""):
        self.mode = mode
        self.pd = parse_diff(data) if not message else ParsedDiff()
        self.title.setText(title)
        if self.pd.added or self.pd.removed:
            self.stat.setText(f"<span style='color:{theme.C['ok']}'>+{self.pd.added}</span>  "
                              f"<span style='color:{theme.C['danger']}'>−{self.pd.removed}</span>")
        else:
            self.stat.setText("")
        self._data, self._message = data, message
        self._render()
        self._update_buttons()

    # Shared between every DiffView so the choice sticks across pages.
    side_by_side_default = False

    def _use_sbs(self) -> bool:
        # Side-by-side needs a single-file text diff; line staging stays in the unified view.
        return (self.sbs_box.isChecked() and self.pd.files <= 1 and bool(self.pd.hunks)
                and not self._message and len(self._data) <= MAX_DISPLAY)

    def _render(self):
        if self._use_sbs():
            self.sbs.load(self.pd)
            self.stack.setCurrentWidget(self.sbs)
        else:
            self.edit.load(self._data, self.pd, self._message)
            self.stack.setCurrentWidget(self.edit)

    def _toggle_sbs(self, on: bool):
        DiffView.side_by_side_default = on
        self._render()
        self._update_buttons()

    def clear(self, msg: str = ""):
        self.set_diff(b"", "readonly", "", msg or " ")

    def _can_edit(self) -> bool:
        return (self.mode in ("unstaged", "staged") and bool(self.pd.hunks) and not self.ignore_ws
                and self.pd.files <= 1 and self.applier is not None and self.stack.currentWidget() is self.edit)

    def _update_buttons(self):
        ok = self._can_edit()
        staged = self.mode == "staged"
        self.btn_hunk.setText(t("diff.unstage_hunk") if staged else t("diff.stage_hunk"))
        self.btn_lines.setText(t("diff.unstage_lines") if staged else t("diff.stage_lines"))
        for b in (self.btn_hunk, self.btn_lines):
            b.setEnabled(ok)
        self.btn_discard.setEnabled(ok and self.mode == "unstaged")

    def _selection(self, whole_hunk: bool) -> dict[int, Optional[set[int]]]:
        a, b = self.edit.selected_blocks()
        sel: dict[int, Optional[set[int]]] = {}
        rows = self.edit.rows
        for i in range(a, min(b, len(rows) - 1) + 1):
            kind, hi, li, _, _ = rows[i]
            if hi < 0:
                continue
            if whole_hunk or kind == "hunk":
                sel[hi] = None
            elif kind in ("add", "del"):
                if sel.get(hi, set()) is not None:
                    sel.setdefault(hi, set()).add(li)  # type: ignore[union-attr]
        return sel

    def _apply(self, whole_hunk: bool, discard: bool):
        if not self._can_edit():
            return
        sel = self._selection(whole_hunk)
        if not sel:
            return
        if discard:
            reverse, cached = True, False
        elif self.mode == "staged":
            reverse, cached = True, True
        else:
            reverse, cached = False, True
        patch = build_patch(self.pd, sel, reverse)
        if patch and self.applier:
            self.applier(patch, cached, reverse, discard)

    def _menu(self, pos):
        m = QMenu(self)
        if self._can_edit():
            staged = self.mode == "staged"
            m.addAction(t("diff.unstage_hunk") if staged else t("diff.stage_hunk"), lambda: self._apply(True, False))
            m.addAction(t("diff.unstage_lines") if staged else t("diff.stage_lines"),
                        lambda: self._apply(False, False))
            if not staged:
                m.addSeparator()
                m.addAction(t("diff.discard_hunk"), lambda: self._apply(True, True))
                m.addAction(t("diff.discard_lines"), lambda: self._apply(False, True))
            m.addSeparator()
        m.addAction(t("common.copy"), self.edit.copy)
        m.addAction(t("common.select_all"), self.edit.selectAll)
        m.exec(self.edit.mapToGlobal(pos))
