"""CI & Releases dashboard for the current repository, for any supported hosting provider."""
from __future__ import annotations

import os
import webbrowser
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QMenu,
                               QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ...common.i18n import t
from ...core.hosting import PROVIDER_NAMES, RemoteInfo
from ...services.accounts import AccountStore
from ...services.providers import ProviderClient, client_for_remote
from ...services.release import write_workflow_template
from .. import theme

if TYPE_CHECKING:
    from ..repo.view import RepoView

STATUS_ICON = {"success": ("✔", "ok"), "failure": ("✖", "danger"), "cancelled": ("⦸", "muted"),
               "skipped": ("↷", "muted"), "running": ("◐", "accent2"), "queued": ("…", "warn"),
               "manual": ("✋", "warn"), "neutral": ("○", "muted")}


def _parse_time(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _duration(a: Optional[str], b: Optional[str]) -> str:
    s, e = _parse_time(a), _parse_time(b) or datetime.now(timezone.utc)
    if not s:
        return ""
    sec = max(0, int((e - s).total_seconds()))
    return f"{sec // 60}m {sec % 60:02d}s" if sec >= 60 else f"{sec}s"


def _local(s: Optional[str]) -> str:
    d = _parse_time(s)
    return d.astimezone().strftime("%m-%d %H:%M") if d else ""


class ActionsPage(QWidget):
    def __init__(self, rw: "RepoView"):
        super().__init__()
        self.rw = rw
        self.client: Optional[ProviderClient] = None
        self.info: Optional[RemoteInfo] = None
        self.runs: list[dict] = []
        self.loaded = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        bar = QHBoxLayout()
        self.title = QLabel("")
        self.title.setStyleSheet("font-size: 15px; font-weight: 700;")
        bar.addWidget(self.title, 1)
        self.b_refresh = QPushButton("⟳ " + t("common.refresh"))
        self.b_run = QPushButton("▶ " + t("gh.run_workflow"))
        self.b_pr = QPushButton("⤴ " + t("ci.new_pr"))
        self.b_web = QPushButton("🌐 " + t("ci.open_ci"))
        self.b_login = QPushButton("👤 " + t("acc.add"))
        self.b_template = QPushButton("✨ " + t("gh.template"))
        for b in (self.b_refresh, self.b_run, self.b_pr, self.b_web, self.b_login, self.b_template):
            bar.addWidget(b)
        lay.addLayout(bar)
        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        self.notice.setObjectName("muted")
        lay.addWidget(self.notice)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        split = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["", t("gh.workflow"), t("gh.title"), t("common.branch"), t("gh.event"),
                                              t("gh.started"), t("gh.duration")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        for c, w in ((0, 36), (1, 170), (3, 130), (4, 110), (5, 110), (6, 90)):
            self.table.setColumnWidth(c, w)
        split.addWidget(self.table)
        self.jobs = QTreeWidget()
        self.jobs.setHeaderLabels([t("gh.job"), t("gh.status"), t("gh.duration")])
        self.jobs.setColumnWidth(0, 460)
        split.addWidget(self.jobs)
        split.setSizes([420, 300])
        self.tabs.addTab(split, "⚙ CI")

        self.rel = QTableWidget(0, 5)
        self.rel.setHorizontalHeaderLabels([t("gh.release"), "Tag", t("gh.published"), t("gh.assets"), t("gh.kind")])
        self.rel.verticalHeader().setVisible(False)
        self.rel.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rel.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rel.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabs.addTab(self.rel, "🚀 Releases")

        self.timer = QTimer(self)
        self.timer.setInterval(15000)
        self.timer.timeout.connect(lambda: self.isVisible() and self.reload(quiet=True))
        self.b_refresh.clicked.connect(lambda: self.reload())
        self.b_web.clicked.connect(lambda: self.info and webbrowser.open(self.info.ci_url))
        self.b_pr.clicked.connect(self._new_pr)
        self.b_login.clicked.connect(lambda: self.rw.main.accounts_dialog(self.info))
        self.b_run.clicked.connect(self._dispatch)
        self.b_template.clicked.connect(self._template)
        self.table.itemSelectionChanged.connect(self._load_jobs)
        self.table.doubleClicked.connect(lambda _: self._open_run())
        self.table.customContextMenuRequested.connect(self._menu)
        self.rel.doubleClicked.connect(self._open_release)
        self.jobs.itemDoubleClicked.connect(lambda it, _c: it.data(0, Qt.UserRole) and
                                            webbrowser.open(it.data(0, Qt.UserRole)))

    def showEvent(self, e):
        super().showEvent(e)
        if not self.loaded:
            self.reload()

    def reload(self, quiet: bool = False):
        self.loaded = True
        repo, store = self.rw.repo, AccountStore(self.rw.main.cfg)
        has_wf = any(os.path.exists(os.path.join(repo.path, p)) for p in
                     (".github/workflows", ".gitlab-ci.yml", "bitbucket-pipelines.yml", ".gitea/workflows",
                      ".forgejo/workflows", "azure-pipelines.yml"))
        self.b_template.setVisible(not has_wf)
        if not self.title.text():
            self.title.setText("⏳ " + t("gh.loading") + "…")

        def work():
            info, acc = store.for_repo(repo)
            if not info:
                return None, None, "", [], [], ""
            token, user, src = store.token_for(info.provider, info.host, acc.username if acc else "")
            client = client_for_remote(info, token, user)
            runs, rels, err = [], [], ""
            try:
                if "ci" in client.FEATURES:
                    runs = client.ci_runs()
                if "releases" in client.FEATURES:
                    rels = client.releases()
            except Exception as e:  # noqa: BLE001
                err = str(e)
            return info, client, src, runs, rels, err

        def done(res):
            info, client, src, runs, rels, err = res
            self.info, self.client = info, client
            for b in (self.b_run, self.b_pr, self.b_web):
                b.setEnabled(info is not None)
            if not info:
                self.title.setText("CI & Releases")
                self.notice.setText("ℹ " + t("ci.no_remote"))
                self.b_login.hide()
                return
            name = PROVIDER_NAMES.get(info.provider, info.provider)
            self.title.setText(f"  {name} · {info.host} / {info.path}")
            self.b_run.setEnabled("dispatch" in client.FEATURES)
            self.b_login.setVisible(not client.token)
            notes = []
            if not client.token:
                notes.append("🔑 " + t("ci.no_token", provider=name))
            elif src:
                notes.append(t("ci.token_from", src=src))
            if "ci" not in client.FEATURES:
                notes.append("ℹ " + t("ci.no_api", provider=name))
            if err:
                notes.append("⚠ " + err)
            self.notice.setText("   ·   ".join(notes))
            self.runs = runs
            self._fill_runs()
            self._fill_releases(rels)
            active = any(r["status"] in ("running", "queued") for r in runs)
            self.timer.start() if active else self.timer.stop()

        def fail(e):
            self.notice.setText("⚠ " + str(e))
            self.timer.stop()
        self.rw.bg(work, done, fail, label="" if quiet else t("gh.loading"))

    def _fill_runs(self):
        cur = self._run()
        cur_id = cur.get("id") if cur else None
        self.table.setRowCount(len(self.runs))
        for i, r in enumerate(self.runs):
            icon, ckey = STATUS_ICON.get(r["status"], ("○", "muted"))
            vals = [icon, r.get("name", ""), r.get("title", ""), r.get("branch", ""), r.get("event", ""),
                    _local(r.get("started")), _duration(r.get("started"), r.get("updated") if r.get("done") else None)]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(str(v or ""))
                if j == 0:
                    it.setForeground(QColor(theme.C[ckey]))
                    it.setTextAlignment(Qt.AlignCenter)
                    it.setToolTip(r["status"])
                self.table.setItem(i, j, it)
            if r.get("id") == cur_id:
                self.table.selectRow(i)
        if self.runs and cur_id is None:
            self.table.selectRow(0)
        if not self.runs:
            self.jobs.clear()

    def _fill_releases(self, rels: list[dict]):
        self.rel.setRowCount(len(rels))
        kinds = {"draft": t("gh.draft"), "prerelease": t("gh.prerelease"), "stable": t("gh.stable")}
        for i, r in enumerate(rels):
            vals = [r["name"], r["tag"], _local(r.get("published")), str(r.get("assets", 0)),
                    kinds.get(r.get("kind", ""), "")]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setData(Qt.UserRole, r.get("url"))
                self.rel.setItem(i, j, it)

    def _run(self) -> Optional[dict]:
        r = self.table.currentRow()
        return self.runs[r] if 0 <= r < len(self.runs) else None

    def _load_jobs(self):
        run, client = self._run(), self.client
        self.jobs.clear()
        if not run or not client:
            return
        rid = run["id"]

        def add(parent, j):
            icon, ckey = STATUS_ICON.get(j["status"], ("○", "muted"))
            it = QTreeWidgetItem([f"{icon}  {j['name']}", j["status"], _duration(j.get("started"), j.get("finished"))])
            it.setForeground(0, QColor(theme.C[ckey]))
            it.setData(0, Qt.UserRole, j.get("url"))
            (parent.addChild(it) if parent else self.jobs.addTopLevelItem(it))
            for s in j.get("steps", []):
                add(it, s)
            it.setExpanded(j["status"] not in ("success", "skipped"))

        def done(jobs):
            cur = self._run()
            if not cur or cur["id"] != rid:
                return
            self.jobs.clear()
            for j in jobs:
                add(None, j)
        self.rw.bg(lambda: client.ci_jobs(rid), done, lambda e: None, label="")

    def _menu(self, pos):
        run = self._run()
        if not run or not self.client:
            return
        m = QMenu(self)
        m.addAction("🌐 " + t("gh.open_run"), self._open_run)
        if "ci_control" in self.client.FEATURES:
            m.addSeparator()
            m.addAction("⟳ " + t("gh.rerun"), lambda: self._act("rerun", run))
            m.addAction("⟳ " + t("gh.rerun_failed"), lambda: self._act("rerun_failed", run))
            if not run.get("done"):
                m.addAction("⦸ " + t("gh.cancel"), lambda: self._act("cancel", run))
        if run.get("sha"):
            m.addSeparator()
            m.addAction(t("gh.show_commit"), lambda: self.rw.show_commit(run["sha"]))
        m.exec(self.table.viewport().mapToGlobal(pos))

    def _need_token(self) -> bool:
        if self.client and self.client.token:
            return False
        QMessageBox.information(self, "CI", t("ci.no_token", provider=PROVIDER_NAMES.get(
            self.info.provider if self.info else "", "")))
        return True

    def _act(self, what: str, run: dict):
        c = self.client
        if not c or self._need_token():
            return
        fn = {"rerun": lambda: c.ci_rerun(run["id"]), "rerun_failed": lambda: c.ci_rerun(run["id"], True),
              "cancel": lambda: c.ci_cancel(run["id"])}[what]
        self.rw.bg(fn, lambda _: QTimer.singleShot(1500, self.reload), None, label=t("gh.working"))

    def _open_run(self):
        run = self._run()
        if run and run.get("url"):
            webbrowser.open(run["url"])

    def _open_release(self, idx):
        it = self.rel.item(idx.row(), 0)
        if it and it.data(Qt.UserRole):
            webbrowser.open(it.data(Qt.UserRole))

    def _new_pr(self):
        if not self.info:
            return
        branch = self.rw.repo.current_branch() or ""
        webbrowser.open(self.info.new_pr_url(branch))

    def _dispatch(self):
        c = self.client
        if not c or self._need_token():
            return

        def got(wfs):
            if not wfs:
                QMessageBox.information(self, "CI", t("gh.no_workflows"))
                return
            names = [w["name"] for w in wfs]
            name, ok = QInputDialog.getItem(self, t("gh.run_workflow"), t("gh.pick_workflow"), names, 0, False)
            if not ok:
                return
            wf = wfs[names.index(name)]
            ref, ok = QInputDialog.getText(self, t("gh.run_workflow"), t("gh.ref"),
                                           text=self.rw.repo.current_branch() or "main")
            if not ok or not ref.strip():
                return
            self.rw.bg(lambda: c.ci_dispatch(wf["id"], ref.strip()),
                       lambda _: (self.rw.main.toast(t("gh.dispatched")), QTimer.singleShot(3000, self.reload)),
                       None, label=t("gh.working"))
        self.rw.bg(c.ci_workflows, got, None, label=t("gh.loading"))

    def _template(self):
        provider = self.info.provider if self.info else "github"
        try:
            rel = write_workflow_template(self.rw.repo.path, provider)
        except FileExistsError as e:
            QMessageBox.information(self, "CI", t("gh.template_exists", path=str(e)))
            return
        self.rw.main.toast(t("gh.template_done", path=rel))
        self.rw.refresh()
        self.rw.open_in_editor(os.path.join(self.rw.repo.path, rel))
