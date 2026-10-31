"""History table model and the delegate that paints lanes, nodes, badges and avatars."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                           QPen, QRadialGradient)
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from ...common.i18n import t
from ...common.text import initials, relative_time
from ...core.graph_layout import GraphRow, layout
from ...core.models import Commit
from .. import theme
from ..display import avatar_color


LANE_W = 16


COLORS = [QColor(c) for c in ("#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#60a5fa", "#fb923c",
                              "#e879f9", "#2dd4bf", "#f87171", "#a3e635", "#818cf8")]


class HistoryModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.commits: list[Commit] = []
        self.rows: list[GraphRow] = []
        self.head = ""
        self.remotes: set[str] = set()
        self.highlight: set[int] = set()
        self.dim: set[int] = set()
        self.headers = [t("hist.col.subject"), t("hist.col.author"), t("hist.col.date"), t("hist.col.sha")]

    def set_commits(self, commits: list[Commit], head: str, remotes: set[str], graph: bool = True):
        self.beginResetModel()
        self.commits = commits
        self.rows = layout(commits) if graph else [GraphRow(0, 0, [], [], 1, len(c.parents) > 1) for c in commits]
        self.head = head
        self.remotes = remotes
        self.highlight = set()
        self.dim = set()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.commits)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def headerData(self, s, o, role=Qt.DisplayRole):
        if o == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[s]
        return None

    def data(self, idx, role=Qt.DisplayRole):
        if not idx.isValid():
            return None
        c = self.commits[idx.row()]
        col = idx.column()
        if role == Qt.DisplayRole:
            if col == 0:
                return c.subject
            if col == 1:
                return c.author
            if col == 2:
                return relative_time(c.timestamp)
            if col == 3:
                return c.short
        if role == Qt.ToolTipRole:
            when = datetime.fromtimestamp(c.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            return f"{c.sha}\n{c.author} <{c.email}>\n{when}\n\n{c.subject}"
        if role == Qt.FontRole:
            if c.sha == self.head:
                f = QFont()
                f.setBold(True)
                return f
            if col == 3:
                return QFont("Consolas", 9)
        if role == Qt.BackgroundRole and idx.row() in self.highlight:
            return QBrush(QColor(theme.C["warn"]).darker(300) if theme.CURRENT != "light" else QColor("#fff3c4"))
        if role == Qt.ForegroundRole:
            if idx.row() in self.dim:
                return QBrush(theme.color("muted").darker(130))
            if col in (2, 3):
                return QBrush(theme.color("muted"))
        return None

    def badges(self, c: Commit) -> list[tuple[str, str]]:
        res = []
        for r in c.refs:
            if r.startswith("HEAD -> "):
                res.append(("head", r[8:]))
            elif r == "HEAD":
                res.append(("detached", "HEAD"))
            elif r.startswith("tag: "):
                res.append(("tag", r[5:]))
            elif r.endswith("/HEAD"):
                continue
            elif r.split("/", 1)[0] in self.remotes:
                res.append(("remote", r))
            else:
                res.append(("local", r))
        return res


BADGE = {
    "head": ("#10b981", "#34d399", "#ffffff", "● "),
    "local": ("#6d28d9", "#8b5cf6", "#ffffff", ""),
    "remote": ("#334155", "#475569", "#e2e8f0", "☁ "),
    "tag": ("#b45309", "#f59e0b", "#ffffff", "◆ "),
    "detached": ("#be123c", "#f43f5e", "#ffffff", "⚠ "),
}


class GraphDelegate(QStyledItemDelegate):
    def __init__(self, model: HistoryModel, parent=None):
        super().__init__(parent)
        self.model = model

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QSize(s.width(), max(s.height(), 28))

    def paint(self, p: QPainter, opt, idx):
        if idx.column() == 1:
            return self._paint_author(p, opt, idx)
        if idx.column() != 0:
            return super().paint(p, opt, idx)
        row = idx.row()
        c = self.model.commits[row]
        g = self.model.rows[row]
        p.save()
        style = opt.widget.style() if opt.widget else None
        self.initStyleOption(opt, idx)
        text = opt.text
        opt.text = ""
        if style:
            style.drawControl(QStyle.CE_ItemViewItem, opt, p, opt.widget)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = opt.rect
        x0 = r.left() + 8
        top, bot = r.top(), r.bottom() + 1
        mid = (top + bot) / 2

        def cx(col):
            return x0 + col * LANE_W + LANE_W / 2

        for a, b, ci in g.top:
            self._edge(p, cx(a), top, cx(b), mid, COLORS[ci % len(COLORS)])
        for a, b, ci in g.bottom:
            self._edge(p, cx(a), mid, cx(b), bot, COLORS[ci % len(COLORS)])
        color = COLORS[g.color % len(COLORS)]
        center = QPointF(cx(g.col), mid)
        is_head = c.sha == self.model.head
        if is_head:
            glow = QRadialGradient(center, 12)
            gc = QColor(color)
            gc.setAlpha(150)
            glow.setColorAt(0, gc)
            gc.setAlpha(0)
            glow.setColorAt(1, gc)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(center, 12, 12)
        p.setPen(QPen(theme.color("bg"), 2))
        p.setBrush(QColor("#ffffff") if is_head else color)
        rad = 5.5 if not g.merge else 4
        if g.merge:
            p.setBrush(theme.color("bg"))
            p.setPen(QPen(color, 2.2))
        p.drawEllipse(center, rad, rad)

        x = x0 + g.width * LANE_W + 8
        fm = QFontMetrics(opt.font)
        bf = QFont(opt.font)
        bf.setPointSizeF(max(7.0, opt.font.pointSizeF() - 1))
        bf.setBold(True)
        bfm = QFontMetrics(bf)
        for kind, name in self.model.badges(c):
            c1, c2, fg, icon = BADGE[kind]
            label = icon + name
            w = bfm.horizontalAdvance(label) + 14
            if x + w > r.right() - 60:
                break
            br = QRectF(x, mid - 10, w, 20)
            grad = QLinearGradient(br.topLeft(), br.topRight())
            grad.setColorAt(0, QColor(c1))
            grad.setColorAt(1, QColor(c2))
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(br, 10, 10)
            p.setPen(QColor(fg))
            p.setFont(bf)
            p.drawText(br, Qt.AlignCenter, label)
            x += w + 5
        p.setFont(opt.font)
        sel = opt.state & QStyle.State_Selected
        fgc = opt.palette.highlightedText().color() if sel else opt.palette.text().color()
        if row in self.model.dim and not sel:
            fgc = theme.color("muted")
        p.setPen(fgc)
        tr = QRectF(x + 2, top, max(0, r.right() - x - 4), bot - top)
        p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, fm.elidedText(text, Qt.ElideRight, int(tr.width())))
        p.restore()

    def _paint_author(self, p: QPainter, opt, idx):
        c = self.model.commits[idx.row()]
        p.save()
        self.initStyleOption(opt, idx)
        opt.text = ""
        style = opt.widget.style() if opt.widget else None
        if style:
            style.drawControl(QStyle.CE_ItemViewItem, opt, p, opt.widget)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = opt.rect
        d = 20
        ar = QRectF(r.left() + 6, r.center().y() - d / 2 + 1, d, d)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(avatar_color(c.email or c.author)))
        p.drawEllipse(ar)
        f = QFont(opt.font)
        f.setPointSizeF(7)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(ar, Qt.AlignCenter, initials(c.author))
        p.setFont(opt.font)
        sel = opt.state & QStyle.State_Selected
        p.setPen(opt.palette.highlightedText().color() if sel else theme.color("text"))
        tr = QRectF(ar.right() + 6, r.top(), r.right() - ar.right() - 8, r.height())
        p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft,
                   QFontMetrics(opt.font).elidedText(c.author, Qt.ElideRight, int(tr.width())))
        p.restore()

    @staticmethod
    def _edge(p: QPainter, x1, y1, x2, y2, color: QColor):
        p.setPen(QPen(color, 2.2, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        if x1 == x2:
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            return
        path = QPainterPath(QPointF(x1, y1))
        ym = (y1 + y2) / 2
        path.cubicTo(QPointF(x1, ym), QPointF(x2, ym), QPointF(x2, y2))
        p.drawPath(path)
