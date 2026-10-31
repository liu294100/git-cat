"""RepoView: one open repository = sidebar + page navigation; operations come from the mixins."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QSplitter, QStackedWidget,
                               QToolButton, QVBoxLayout, QWidget)

from ...common.i18n import t
from ...core.models import Ref
from ...core.repo import Repo
from ...core.stats import timeline_from
from ...services.accounts import AccountStore
from ...services.snapshot import Snapshot, load_snapshot
from ..dialogs.accounts import PROVIDER_ICON
from ..pages.actions import ActionsPage
from ..pages.files import FilesPage
from ..pages.history import HistoryPage
from ..pages.insights import InsightsPage
from ..pages.stash import StashPage
from ..pages.working import WorkingPage
from ..sidebar import Sidebar
from .ops_branch import BranchOps
from .ops_history import HistoryOps
from .ops_release import ReleaseOps
from .ops_remote import RemoteOps
from .ops_stash import StashOps
from .ops_working import WorkingOps

if TYPE_CHECKING:
    from ..main_window import MainWindow

PAGES = ["work", "history", "files", "stash", "actions", "insights"]
ICONS = ["✎", "⌥", "🗂", "📦", "⚙", "📊"]


class RepoView(QWidget, WorkingOps, HistoryOps, BranchOps, ReleaseOps, RemoteOps, StashOps):
    def __init__(self, main: "MainWindow", repo: Repo):
        super().__init__()
        self.main = main
        self.repo = repo
        self.last_refs: list[Ref] = []
        self._sig: Optional[tuple] = None
        self._loading = False
        self._pending: Optional[bool] = None  # queued refresh (value = force_log)
        self.setObjectName("root")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split)
        self.sidebar = Sidebar(self)
        split.addWidget(self.sidebar)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 6, 6, 0)
        rl.setSpacing(6)
        self.banner = QFrame()
        self.banner.setObjectName("banner")
        self.banner_box = QHBoxLayout(self.banner)
        self.banner_box.setContentsMargins(12, 6, 8, 6)
        self.banner_label = QLabel("")
        self.banner_box.addWidget(self.banner_label, 1)
        self.banner_buttons: list[QPushButton] = []
        self.banner.hide()
        rl.addWidget(self.banner)

        nav = QHBoxLayout()
        nav.setSpacing(6)
        self.nav_group = QButtonGroup(self)
        self.nav: dict[str, QToolButton] = {}
        for key, icon in zip(PAGES, ICONS):
            b = QToolButton()
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setText(f"{icon}  {t('nav.' + key)}")
            b.clicked.connect(lambda _=False, k=key: self.show_page(k))
            self.nav_group.addButton(b)
            nav.addWidget(b)
            self.nav[key] = b
        nav.addStretch(1)
        self.account_pill = QPushButton("")
        self.account_pill.setObjectName("pill")
        self.account_pill.setToolTip(t("acc.title"))
        self.account_pill.clicked.connect(lambda: main.accounts_dialog(self.remote_info()))
        nav.addWidget(self.account_pill)
        self.path_label = QLabel(repo.path)
        self.path_label.setObjectName("muted")
        nav.addWidget(self.path_label)
        rl.addLayout(nav)

        self.stack = QStackedWidget()
        self.work = WorkingPage(self)
        self.history = HistoryPage(self)
        self.files = FilesPage(self)
        self.stash_page = StashPage(self)
        self.actions = ActionsPage(self)
        self.insights = InsightsPage(self)
        for w in (self.work, self.history, self.files, self.stash_page, self.actions, self.insights):
            self.stack.addWidget(w)
        rl.addWidget(self.stack, 1)
        split.addWidget(right)
        split.setSizes([280, 1200])
        split.setStretchFactor(1, 1)
        last = main.cfg.get("last_page", "history")
        self.show_page(last if last in PAGES else "history")
        QTimer.singleShot(0, lambda: self.refresh(force_log=True))

    # ---------------------------------------------------------------- navigation
    def show_page(self, key: str):
        if key not in PAGES:
            return
        self.nav[key].setChecked(True)
        self.stack.setCurrentIndex(PAGES.index(key))
        self.main.cfg["last_page"] = key
        if key == "insights":
            self._load_insights()

    def show_commit(self, sha: str):
        self.show_page("history")
        if self.history.searching:
            self.history.search.clear()
        if not self.history.select_sha(sha, quiet=True):
            self.history.all_branches.setChecked(True)
            self._after_log = sha
            self.refresh(force_log=True)

    # ---------------------------------------------------------------- refresh (async, coalesced)
    def refresh(self, force_log: bool = False):
        """Load a snapshot in the thread pool. Calls during a load are merged into one follow-up load."""
        if self._loading:
            self._pending = bool(self._pending) or force_log
            return
        if not os.path.isdir(self.repo.path):
            self.main.status(t("err.repo_gone", path=self.repo.path))
            return
        self._loading = True
        repo, all_refs = self.repo, self.history.all_branches.isChecked()
        limit, sig = int(self.main.cfg.get("log_limit", 3000)), self._sig
        if self.history.searching:
            force_log, sig = False, self._sig  # keep search results; signature unchanged → no log reload

        def done(snap: Snapshot):
            self._loading = False
            self._apply(snap)
            self._drain()

        def fail(e):
            self._loading = False
            self.main.status("⚠ " + str(e)[:200])
            self._drain()
        self.main.run_job(lambda: load_snapshot(repo, all_refs, limit, sig, force_log), done, fail, "", quiet=True)

    def _drain(self):
        if self._pending is not None:
            force, self._pending = self._pending, None
            self.refresh(force)

    def _apply(self, s: Snapshot):
        self.last_refs = s.refs
        self.work.fill(s.changes)
        self.work.set_recent(s.recent)
        n = len(s.changes)
        self.nav["work"].setText("✎  " + t("nav.work") + (f"  ·  {n}" if n else ""))
        self.nav["stash"].setText("📦  " + t("nav.stash") + (f"  ·  {len(s.stashes)}" if s.stashes else ""))
        self.stash_page.fill(s.stashes)
        st = s.state
        label = t(f"state.{st.kind}") if st.kind else (t("state.bisecting") if st.bisecting else "")
        self.sidebar.fill(s.refs, s.remotes, s.stashes, s.submodules, s.worktrees, s.branch, s.ahead, s.behind, label)
        self._update_banner(st)
        self._bound_account = s.account
        self.update_account_pill(s.remotes)
        self.files.reload_if_worktree()
        if s.commits is not None and not self.history.searching:
            self._sig = s.signature
            self.history.set_commits(s.commits, s.head, set(s.remotes), graph=self.history.first_parent.isChecked())
            target = getattr(self, "_after_log", None)
            if target:
                self._after_log = None
                self.history.select_sha(target)
        self.main.repo_changed(self, s)

    def update_account_pill(self, remotes: Optional[dict] = None):
        remotes = remotes if remotes is not None else self.repo.remotes()
        url = remotes.get("origin") or next(iter(remotes.values()), "")
        store = AccountStore(self.main.cfg)
        info = store.parse(url) if url else None
        if not info:
            self.account_pill.setVisible(bool(url))
            self.account_pill.setText("🌐 " + t("acc.local_remote") if url else "")
            return
        bound = getattr(self, "_bound_account", "")
        acc = store.get(bound) if bound else store.for_host(info.host)
        icon = PROVIDER_ICON.get(info.provider, "🌐")
        who = acc.username or acc.name if acc else t("acc.not_signed_in")
        self.account_pill.setText(f"{icon}  {who} · {info.host}")
        self.account_pill.setVisible(True)

    def _update_banner(self, st):
        for b in self.banner_buttons:
            b.deleteLater()
        self.banner_buttons = []
        if st.kind:
            self.banner_label.setText("⚠  " + t("banner.in_progress", op=t(f"state.{st.kind}")))
            acts = [(t("banner.continue"), self.continue_op, "primary"), (t("banner.abort"), self.abort_op, "danger")]
            if st.rebasing or st.cherry_picking:
                acts.insert(1, (t("banner.skip"), self.skip_op, ""))
        elif st.bisecting:
            self.banner_label.setText("🔬  " + t("banner.bisect"))
            acts = [(t("bisect.good"), lambda: self.bisect("good"), "primary"),
                    (t("bisect.bad"), lambda: self.bisect("bad"), "danger"),
                    (t("bisect.skip"), lambda: self.bisect("skip"), ""),
                    (t("bisect.reset"), lambda: self.bisect("reset"), "")]
        else:
            self.banner.hide()
            return
        for text, fn, obj in acts:
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(fn)
            self.banner_box.addWidget(b)
            self.banner_buttons.append(b)
        self.banner.show()

    def _load_insights(self):
        repo = self.repo

        def work():
            stats = repo.stats()
            counts = {"local": 0, "remote": 0, "tag": 0}
            for r in repo.refs():
                counts[r.kind] = counts.get(r.kind, 0) + 1
            counts["stash"] = len(repo.stashes())
            return stats, counts, timeline_from(repo.log(max_count=5000, all_refs=False))
        self.bg(work, lambda res: self.insights.fill(*res), lambda e: None, t("ins.loading"))
