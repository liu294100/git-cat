"""Repository insights dashboard."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ...common.i18n import t
from ..widgets.common import BarChart

if TYPE_CHECKING:
    from ..repo.view import RepoView


class InsightsPage(QScrollArea):
    def __init__(self, rw: "RepoView"):
        super().__init__()
        self.rw = rw
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.body = QWidget()
        self.body.setObjectName("root")
        self.setWidget(self.body)
        self.lay = QVBoxLayout(self.body)
        self.lay.setContentsMargins(24, 20, 24, 20)
        self.lay.setSpacing(16)

    def fill(self, stats: dict, refs_count: dict, timeline: list[tuple[str, int]]):
        while self.lay.count():
            it = self.lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        title = QLabel("📊  " + t("ins.title"))
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.lay.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(14)
        cards = [(t("ins.commits"), stats.get("commits", 0)), (t("ins.contributors"), len(stats.get("authors", []))),
                 (t("ins.branches"), refs_count.get("local", 0)), (t("ins.remote_branches"), refs_count.get("remote", 0)),
                 (t("ins.tags"), refs_count.get("tag", 0)), (t("ins.stashes"), refs_count.get("stash", 0))]
        for i, (name, v) in enumerate(cards):
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 14, 18, 14)
            num = QLabel(str(v))
            num.setObjectName("stat")
            lb = QLabel(name)
            lb.setObjectName("muted")
            cl.addWidget(num)
            cl.addWidget(lb)
            grid.addWidget(card, i // 3, i % 3)
        self.lay.addLayout(grid)
        for caption, data in ((t("ins.top_authors"), [(who, n) for n, who in stats.get("authors", [])]),
                              (t("ins.activity"), timeline)):
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 14, 18, 14)
            lb = QLabel(caption)
            lb.setObjectName("section")
            cl.addWidget(lb)
            cl.addWidget(BarChart(data))
            self.lay.addWidget(card)
        self.lay.addStretch(1)
