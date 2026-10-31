"""Main window: header bar, repository tabs, welcome screen, background job runner, console, updates."""
from __future__ import annotations

import os
import sys
import time
import webbrowser
from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QFileSystemWatcher, QPropertyAnimation, Qt, QThreadPool, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QFileDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QStackedWidget, QTabWidget,
                               QToolButton, QVBoxLayout, QWidget)

from .. import APP_NAME, GITHUB_REPOSITORY, __version__
from ..common.config import save_config
from ..common.i18n import LANGUAGES, t
from ..common.system import git_version, open_terminal, reveal_in_explorer
from ..core.repo import Repo
from ..core.runner import GitError, decode, run_git
from ..services import updater
from . import theme
from ..services.accounts import AccountStore
from ..services.providers import client_for
from .dialogs.accounts import AccountsDialog
from .icons import app_icon
from .dialogs.command_center import CommandCenter
from .dialogs.git_ops import CloneDialog
from .dialogs.palette import CommandPalette
from .dialogs.settings import SettingsDialog
from .repo.view import RepoView
from .widgets.diff_view import DiffView
from .workers import Bridge, Job

MAX_RECENT = 30


class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("pillAccent")
        self.setStyleSheet("padding: 10px 18px; border-radius: 14px; font-size: 13px;")
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"opacity", self)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade)
        self.hide()

    def pop(self, text: str, ms: int = 2600):
        self.setText(text)
        self.adjustSize()
        p = self.parentWidget()
        self.move(p.width() - self.width() - 24, p.height() - self.height() - 48)
        self.raise_()
        self.show()
        self.anim.stop()
        self.anim.setDuration(180)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.timer.start(ms)

    def _fade(self):
        self.anim.stop()
        self.anim.setDuration(500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self._done)
        self.anim.start()

    def _done(self):
        try:
            self.anim.finished.disconnect(self._done)
        except (RuntimeError, TypeError):
            pass
        if self.effect.opacity() < 0.05:
            self.hide()


class WelcomePage(QWidget):
    def __init__(self, main: "MainWindow"):
        super().__init__()
        self.main = main
        self.setObjectName("root")
        outer = QHBoxLayout(self)
        outer.addStretch(1)
        col = QVBoxLayout()
        col.setSpacing(14)
        col.addStretch(1)
        logo = QLabel()
        pm = app_icon().pixmap(96, 96)
        logo.setPixmap(pm)
        col.addWidget(logo, 0, Qt.AlignLeft)
        hero = QLabel(f"<span>Git</span><span style='color:{theme.C['accent2']}'>Cat</span>")
        hero.setObjectName("hero")
        col.addWidget(hero)
        sub = QLabel(t("welcome.tagline"))
        sub.setObjectName("heroSub")
        col.addWidget(sub)
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        for icon, key, fn in (("📂", "welcome.open", main.open_dialog), ("⬇", "welcome.clone", main.clone_dialog),
                              ("✨", "welcome.init", main.init_dialog)):
            b = QPushButton(f"{icon}   {t(key)}\n      {t(key + '_hint')}")
            b.setObjectName("tile")
            b.setMinimumSize(230, 74)
            b.clicked.connect(fn)
            tiles.addWidget(b)
        col.addLayout(tiles)
        rh = QHBoxLayout()
        lb = QLabel(t("welcome.recent"))
        lb.setObjectName("section")
        rh.addWidget(lb, 1)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("🔎 " + t("common.filter"))
        self.filter.setMaximumWidth(260)
        self.filter.textChanged.connect(self._filter)
        rh.addWidget(self.filter)
        col.addLayout(rh)
        self.recent = QListWidget()
        self.recent.setMinimumSize(720, 260)
        self.recent.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent.itemActivated.connect(lambda it: main.open_repo(it.data(Qt.UserRole)))
        self.recent.customContextMenuRequested.connect(self._menu)
        col.addWidget(self.recent, 1)
        tip = QLabel("💡 " + t("welcome.tip"))
        tip.setObjectName("muted")
        col.addWidget(tip)
        col.addStretch(1)
        outer.addLayout(col, 3)
        outer.addStretch(1)

    def fill(self, paths: list[str]):
        self.recent.clear()
        for p in paths:
            ok = os.path.isdir(p)
            it = QListWidgetItem(f"{'📁' if ok else '⚠'}   {os.path.basename(p) or p}\n        {p}")
            it.setData(Qt.UserRole, p)
            if not ok:
                it.setForeground(theme.color("muted"))
            self.recent.addItem(it)
        self._filter(self.filter.text())

    def _filter(self, q: str):
        q = q.lower()
        for i in range(self.recent.count()):
            it = self.recent.item(i)
            it.setHidden(bool(q) and q not in it.data(Qt.UserRole).lower())

    def _menu(self, pos):
        it = self.recent.itemAt(pos)
        if not it:
            return
        p = it.data(Qt.UserRole)
        m = QMenu(self)
        m.addAction(t("welcome.open"), lambda: self.main.open_repo(p))
        m.addAction(t("file.reveal"), lambda: reveal_in_explorer(p))
        m.addAction(t("welcome.forget"), lambda: self.main.forget_recent(p))
        m.exec(self.recent.mapToGlobal(pos))


class MainWindow(QMainWindow):
    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1560, 960)
        self.setAcceptDrops(True)
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max(4, min(8, (os.cpu_count() or 4))))
        self.bridge = Bridge()
        self.bridge.finished.connect(self._job_done)
        self.bridge.progress.connect(self._job_progress)
        self.bridge.log.connect(self._log)
        self._jobs: dict[int, tuple] = {}
        self._jid = 0
        self._busy: dict[int, str] = {}
        self._pending_update: Optional[updater.ReleaseInfo] = None

        central = QWidget()
        central.setObjectName("root")
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(self._build_header())
        self.stack = QStackedWidget()
        self.welcome = WelcomePage(self)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(lambda _: self._tab_changed())
        plus = QToolButton()
        plus.setText("＋")
        plus.setToolTip(t("welcome.open"))
        plus.clicked.connect(self.show_welcome)
        self.tabs.setCornerWidget(plus, Qt.TopRightCorner)
        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.tabs)
        cl.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self._build_console()
        self._build_menu()
        self._build_status()
        self.toast_w = Toast(central)
        self.welcome.fill(self.cfg.get("recent", []))

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(lambda _: self._watch_timer.start())
        self.watcher.directoryChanged.connect(lambda _: self._watch_timer.start())
        self._watch_timer = QTimer(self)
        self._watch_timer.setSingleShot(True)
        self._watch_timer.setInterval(400)
        self._watch_timer.timeout.connect(lambda: self.current() and self.current().refresh())
        self._last_activate = 0.0
        QApplication.instance().applicationStateChanged.connect(self._app_state)

        self.fetch_timer = QTimer(self)
        self.fetch_timer.timeout.connect(self._auto_fetch)
        self._apply_fetch_timer()
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self.palette)
        QShortcut(QKeySequence("Ctrl+P"), self, self.palette)
        QShortcut(QKeySequence("F5"), self, lambda: self.current() and self.current().refresh(force_log=True))
        QShortcut(QKeySequence("Ctrl+W"), self, lambda: self.close_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Ctrl+Tab"), self, lambda: self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() + 1) % max(1, self.tabs.count())))
        for i in range(9):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, lambda i=i: self.tabs.setCurrentIndex(i))

        for p in self.cfg.get("open_tabs", []):
            if os.path.isdir(p):
                self.open_repo(p, quiet=True)
        if self.tabs.count():
            self.tabs.setCurrentIndex(min(self.cfg.get("active_tab", 0), self.tabs.count() - 1))
        self._update_actions()
        if self.cfg.get("check_updates", True):
            QTimer.singleShot(4000, lambda: self.check_updates(quiet=True))
        if not git_version():
            QTimer.singleShot(300, lambda: QMessageBox.critical(self, APP_NAME, t("err.no_git")))

    # ================================================================ layout
    def _build_header(self) -> QWidget:
        h = QFrame()
        h.setObjectName("header")
        lay = QHBoxLayout(h)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(4)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(28, 28))
        lay.addWidget(logo)
        b1, b2 = QLabel(" Git"), QLabel("Cat")
        b1.setObjectName("brand")
        b2.setObjectName("brandAccent")
        lay.addWidget(b1)
        lay.addWidget(b2)
        lay.addSpacing(18)
        self.tb: dict[str, QToolButton] = {}

        def btn(key, icon, fn, tip_key=None):
            b = QToolButton()
            b.setText(f"{icon}  {t('tb.' + key)}")
            b.setToolTip(t("tb." + (tip_key or key)))
            b.clicked.connect(fn)
            lay.addWidget(b)
            self.tb[key] = b
            return b

        rv = self.current
        btn("fetch", "⟳", lambda: rv() and rv().fetch())
        btn("pull", "⇩", lambda: rv() and rv().quick_pull())
        btn("push", "⇪", lambda: rv() and rv().push())
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {theme.C['border']};")
        lay.addWidget(sep)
        btn("branch", "⎇", lambda: rv() and rv().new_branch())
        btn("merge", "⤵", lambda: rv() and rv().merge())
        btn("stash", "📦", lambda: rv() and rv().stash())
        btn("pop", "📤", lambda: rv() and rv().stash_pop_latest())
        btn("tag", "◆", lambda: rv() and rv().new_tag())
        rel = btn("release", "🚀", lambda: rv() and rv().release())
        rel.setStyleSheet(f"color: {theme.C['accent2']}; font-weight: 700;")
        lay.addStretch(1)
        self.branch_pill = QLabel("")
        self.branch_pill.setObjectName("pill")
        self.branch_pill.hide()
        lay.addWidget(self.branch_pill)
        btn("terminal", "⌨", lambda: rv() and open_terminal(rv().repo.path))
        btn("explorer", "🗂", lambda: rv() and reveal_in_explorer(rv().repo.path))
        pal = QToolButton()
        pal.setText("⌘  " + t("tb.palette"))
        pal.setToolTip("Ctrl+Shift+P")
        pal.clicked.connect(self.palette)
        lay.addWidget(pal)
        return h

    def _build_console(self):
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(5000)
        self.console.setStyleSheet("font-family: Consolas, 'Cascadia Mono', monospace; font-size: 12px;")
        self.dock = QDockWidget(t("console.title"), self)
        self.dock.setObjectName("console")
        self.dock.setWidget(self.console)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock)
        self.dock.hide()

    def _build_status(self):
        sb = self.statusBar()
        self.progress = QProgressBar()
        self.progress.setFixedWidth(200)
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.busy_label = QLabel("")
        sb.addPermanentWidget(self.busy_label)
        sb.addPermanentWidget(self.progress)
        self.sync_label = QLabel("")
        sb.addPermanentWidget(self.sync_label)
        ver = QLabel(f"{APP_NAME} v{__version__}  ·  {git_version()}")
        sb.addPermanentWidget(ver)

    def _build_menu(self):
        mb = self.menuBar()
        rv = self.current

        def act(menu: QMenu, text: str, fn: Callable, shortcut: str = "") -> QAction:
            a = menu.addAction(text)
            a.triggered.connect(lambda _=False: fn())
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            return a

        def on_repo(fn: Callable[[RepoView], None]) -> Callable:
            return lambda: rv() and fn(rv())

        m = mb.addMenu(t("menu.file"))
        act(m, t("welcome.open") + "…", self.open_dialog, "Ctrl+O")
        act(m, t("welcome.clone") + "…", self.clone_dialog, "Ctrl+Shift+O")
        act(m, t("welcome.init") + "…", self.init_dialog)
        m.addSeparator()
        act(m, t("menu.home"), self.show_welcome, "Ctrl+Shift+H")
        act(m, t("settings.title") + "…", self.settings, "Ctrl+,")
        m.addSeparator()
        act(m, t("menu.quit"), self.close, "Ctrl+Q")

        m = mb.addMenu(t("menu.repo"))
        act(m, t("tb.fetch_all"), on_repo(lambda r: r.fetch()), "Ctrl+Shift+F")
        act(m, t("tb.pull") + "…", on_repo(lambda r: r.pull()), "Ctrl+Shift+L")
        act(m, t("tb.push") + "…", on_repo(lambda r: r.push()), "Ctrl+Shift+K")
        m.addSeparator()
        act(m, t("tb.undo"), on_repo(lambda r: r.undo_commit()), "Ctrl+Shift+Z")
        act(m, t("clean.title") + "…", on_repo(lambda r: r.clean()))
        act(m, "Reflog…", on_repo(lambda r: r.reflog()))
        act(m, t("tb.apply_patch") + "…", on_repo(lambda r: r.apply_patches()))
        act(m, t("tb.gitignore"), on_repo(lambda r: r.edit_gitignore()))
        act(m, t("remote.add") + "…", on_repo(lambda r: r.add_remote()))
        act(m, t("wt.add") + "…", on_repo(lambda r: r.add_worktree()))
        m.addSeparator()
        act(m, "⤴ " + t("ci.new_pr"), on_repo(lambda r: r.open_pr(r.repo.current_branch() or "")))
        act(m, "🌐 " + t("remote.open_web"), on_repo(lambda r: r.remote_info() and r.open_url(r.remote_info().web)))
        act(m, "git gc", on_repo(lambda r: r.gc()))

        m = mb.addMenu(t("menu.tools"))
        act(m, "⌨ " + t("cc.title") + "…", lambda: self.command_center(), "Ctrl+Shift+G")
        act(m, t("tb.custom") + "…", on_repo(lambda r: r.run_custom()), "Ctrl+Alt+G")
        m.addSeparator()
        act(m, "⇄ " + t("cmpv.title") + "…", on_repo(lambda r: r.compare_files("", "HEAD", None, "")), "Ctrl+D")
        act(m, "⇄ " + t("cmpv.external") + "…", self.compare_external)
        act(m, "🗂 " + t("nav.files"), on_repo(lambda r: r.show_page("files")), "Ctrl+Shift+E")

        m = mb.addMenu(t("menu.accounts"))
        act(m, "👤 " + t("acc.title") + "…", lambda: self.accounts_dialog(), "Ctrl+Alt+A")
        act(m, "＋ " + t("acc.add") + "…", lambda: self.accounts_dialog(add=True))
        act(m, "📌 " + t("acc.use_for_repo") + "…", on_repo(lambda r: self.accounts_dialog(r.remote_info())))

        m = mb.addMenu(t("menu.branch"))
        act(m, t("branch.new") + "…", on_repo(lambda r: r.new_branch()), "Ctrl+B")
        act(m, t("merge.ok") + "…", on_repo(lambda r: r.merge()), "Ctrl+M")
        act(m, t("tag.new") + "…", on_repo(lambda r: r.new_tag()), "Ctrl+T")
        act(m, t("tag.push_all"), on_repo(lambda r: r.push_all_tags()))
        act(m, "🚀 " + t("release.title") + "…", on_repo(lambda r: r.release()), "Ctrl+R")
        m.addSeparator()
        act(m, t("stash.title") + "…", on_repo(lambda r: r.stash()), "Ctrl+Shift+S")
        act(m, t("stash.pop"), on_repo(lambda r: r.stash_pop_latest()))

        m = mb.addMenu(t("menu.view"))
        for i, key in enumerate(["work", "history", "files", "stash", "actions", "insights"]):
            act(m, t("nav." + key), on_repo(lambda r, k=key: r.show_page(k)), f"Alt+{i + 1}")
        m.addSeparator()
        act(m, t("console.title"), self.show_log, "Ctrl+`")
        tm = m.addMenu(t("settings.theme"))
        for key in theme.THEMES:
            act(tm, t(f"theme.{key}"), lambda k=key: self.set_theme(k))
        lm = m.addMenu("🌐 " + t("settings.language"))
        for code, native in LANGUAGES.items():
            act(lm, native, lambda c=code: self.set_language(c))

        m = mb.addMenu(t("menu.help"))
        act(m, t("menu.check_updates"), lambda: self.check_updates(quiet=False))
        act(m, t("menu.github"), lambda: webbrowser.open(f"https://github.com/{GITHUB_REPOSITORY}"))
        act(m, t("menu.shortcuts"), self.show_shortcuts)
        act(m, t("menu.about"), self.about)

    # ================================================================ accounts / tools
    def accounts_dialog(self, info=None, add: bool = False):
        d = AccountsDialog(self)
        if add:
            d.edit(None)
        elif info is not None and not AccountStore(self.cfg).for_host(info.host):
            d.edit(None, provider=info.provider, host=info.host)  # repo host has no account yet → straight to login
        d.exec()
        save_config(self.cfg)

    def accounts_changed(self):
        for v in self.views():
            v.update_account_pill()

    def command_center(self):
        CommandCenter(self, self.current()).exec()
        save_config(self.cfg)

    def compare_external(self):
        a, _ = QFileDialog.getOpenFileName(self, t("cmpv.left"), os.path.expanduser("~"))
        if not a:
            return
        b, _ = QFileDialog.getOpenFileName(self, t("cmpv.right"), os.path.dirname(a))
        if not b:
            return
        v = self.current()
        if v:
            v.compare_files(a, "", b, "")
            return
        code, out, err = run_git(["diff", "--no-index", "--", a, b], os.path.dirname(a))
        dlg = QDialog(self)
        dlg.setWindowTitle(f"⇄ {os.path.basename(a)} ↔ {os.path.basename(b)}")
        dlg.resize(1300, 820)
        lay = QVBoxLayout(dlg)
        dv = DiffView()
        dv.sbs_box.setChecked(True)
        dv.set_diff(out, "readonly", f"{a}  ⇄  {b}", "" if out.strip() else (decode(err) or t("cmpv.identical")))
        lay.addWidget(dv)
        dlg.exec()

    # ================================================================ repos & tabs
    def current(self) -> Optional[RepoView]:
        w = self.tabs.currentWidget()
        return w if isinstance(w, RepoView) and self.stack.currentWidget() is self.tabs else None

    def views(self) -> list[RepoView]:
        return [self.tabs.widget(i) for i in range(self.tabs.count())]

    def open_repo(self, path: str, quiet: bool = False):
        root = Repo.find_root(path)
        if not root:
            if not quiet:
                if os.path.isdir(path) and QMessageBox.question(self, APP_NAME, t("err.not_repo_init", path=path)) \
                        == QMessageBox.Yes:
                    Repo.init(path)
                    self.open_repo(path)
                elif not os.path.isdir(path):
                    QMessageBox.warning(self, APP_NAME, t("err.not_repo", path=path))
            return
        root = os.path.normpath(root)
        for i, v in enumerate(self.views()):
            if os.path.normcase(v.repo.path) == os.path.normcase(root):
                self.stack.setCurrentWidget(self.tabs)
                self.tabs.setCurrentIndex(i)
                self._tab_changed()
                return
        repo = Repo(root, logger=lambda cmd, code, out, err: self.bridge.log.emit(cmd, code, out, err))
        view = RepoView(self, repo)
        idx = self.tabs.addTab(view, "📁 " + repo.name)
        self.tabs.setTabToolTip(idx, repo.path)
        self.stack.setCurrentWidget(self.tabs)
        self.tabs.setCurrentIndex(idx)
        self._tab_changed()  # currentChanged fired while the welcome page was still showing
        self._remember(root)

    def _remember(self, path: str):
        rec = [p for p in self.cfg.get("recent", []) if os.path.normcase(p) != os.path.normcase(path)]
        self.cfg["recent"] = [path] + rec[:MAX_RECENT - 1]
        self.welcome.fill(self.cfg["recent"])

    def forget_recent(self, path: str):
        self.cfg["recent"] = [p for p in self.cfg.get("recent", []) if p != path]
        self.welcome.fill(self.cfg["recent"])

    def close_tab(self, idx: int):
        if idx < 0:
            return
        w = self.tabs.widget(idx)
        self._watch(None)  # release OS handles on the repo folder before the tab goes away
        self.tabs.removeTab(idx)
        if w:
            w.deleteLater()
        if not self.tabs.count():
            self.show_welcome()

    def show_welcome(self):
        self.welcome.fill(self.cfg.get("recent", []))
        self.stack.setCurrentWidget(self.welcome)
        self._update_actions()

    def _tab_changed(self):
        v = self.current()
        self._update_actions()
        self._watch(v)
        if v:
            self.setWindowTitle(f"{v.repo.name} — {APP_NAME}")
            v.refresh()
        else:
            self.setWindowTitle(APP_NAME)

    def _watch(self, v: Optional[RepoView]):
        old = self.watcher.files() + self.watcher.directories()
        if old:
            self.watcher.removePaths(old)
        if not v:
            return
        try:
            g = v.repo.git_dir
        except GitError:
            return
        paths = [os.path.join(g, n) for n in ("HEAD", "index", "FETCH_HEAD", "ORIG_HEAD", "MERGE_HEAD")]
        paths += [os.path.join(g, "refs", "heads"), os.path.join(g, "refs", "tags"), v.repo.path]
        self.watcher.addPaths([p for p in paths if os.path.exists(p)])

    def _update_actions(self):
        has = self.current() is not None
        for b in self.tb.values():
            b.setEnabled(has)
        if not has:
            self.branch_pill.hide()
            self.sync_label.setText("")

    def repo_changed(self, view: RepoView, snap):
        """Called by RepoView after every snapshot is applied."""
        if view is not self.current():
            return
        idx = self.tabs.indexOf(view)
        dirty = len(snap.changes)
        self.tabs.setTabText(idx, ("● " if dirty else "📁 ") + view.repo.name)
        branch = snap.branch or t("side.detached")
        self.branch_pill.setText(f"⎇  {branch}")
        self.branch_pill.show()
        sync = []
        if snap.ahead:
            sync.append(f"↑{snap.ahead}")
        if snap.behind:
            sync.append(f"↓{snap.behind}")
        self.sync_label.setText(" ".join(sync))
        self.tb["push"].setText("⇪  " + t("tb.push") + (f"  {snap.ahead}" if snap.ahead else ""))
        self.tb["pull"].setText("⇩  " + t("tb.pull") + (f"  {snap.behind}" if snap.behind else ""))
        self.tb["pop"].setEnabled(bool(snap.stashes))

    def _app_state(self, state):
        if state == Qt.ApplicationActive and time.monotonic() - self._last_activate > 1.5:
            self._last_activate = time.monotonic()
            v = self.current()
            if v:
                v.refresh()

    # ================================================================ dialogs
    def open_dialog(self):
        d = QFileDialog.getExistingDirectory(self, t("welcome.open"), self.cfg.get("clone_dir", os.path.expanduser("~")))
        if d:
            self.open_repo(d)

    def clone_dialog(self, url: str = ""):
        d = CloneDialog(self, self.cfg.get("clone_dir", os.path.expanduser("~")), url if isinstance(url, str) else "")
        pick = QPushButton("👤 " + t("clone.from_account"))
        pick.clicked.connect(lambda: self._pick_remote_repo(d))
        d.form.insertRow(1, "", pick)
        if not d.exec():
            return
        url, dest = d.url.text().strip(), d.dest
        depth, branch, rec = d.depth.value(), d.branch.text().strip(), d.recursive.isChecked()
        self.cfg["clone_dir"] = d.parent_dir.text().strip()
        logger = lambda cmd, code, out, err: self.bridge.log.emit(cmd, code, out, err)  # noqa: E731
        self.run_job(lambda p: Repo.clone(url, dest, logger, depth, branch, rec, p),
                     lambda _: (self.open_repo(dest), self.toast(t("clone.done"))),
                     lambda e: QMessageBox.warning(self, t("clone.title"), str(e)), t("clone.title"), progress=True)

    def _pick_remote_repo(self, d: CloneDialog):
        """List repositories of a configured account and put the chosen clone URL into the dialog."""
        store = AccountStore(self.cfg)
        accounts = store.all()
        if not accounts:
            if QMessageBox.question(self, t("clone.title"), t("clone.no_accounts")) == QMessageBox.Yes:
                self.accounts_dialog(add=True)
            return
        labels = [a.label + f"  ({a.provider})" for a in accounts]
        choice, ok = QInputDialog.getItem(self, t("clone.from_account"), t("acc.accounts"), labels, 0, False)
        if not ok:
            return
        acc = accounts[labels.index(choice)]

        def work():
            token, user, _ = store.token_for(acc.provider, acc.host, acc.username)
            return client_for(acc.provider, acc.host, token, user).list_repos()

        def done(repos):
            if not repos:
                QMessageBox.information(self, t("clone.title"), t("clone.no_repos"))
                return
            items = [f"{'🔒' if r['private'] else '🌍'} {r['full_name']}   {r['description'][:60]}" for r in repos]
            sel, ok2 = QInputDialog.getItem(self, t("clone.from_account"), acc.label, items, 0, False)
            if ok2:
                r = repos[items.index(sel)]
                d.url.setText(r["ssh"] if acc.auth == "ssh" and r["ssh"] else r["https"])
        self.run_job(work, done, lambda e: QMessageBox.warning(self, t("clone.title"), str(e)), t("gh.loading"))

    def init_dialog(self):
        d = QFileDialog.getExistingDirectory(self, t("welcome.init"), self.cfg.get("clone_dir", os.path.expanduser("~")))
        if not d:
            return
        if Repo.find_root(d) and os.path.normcase(Repo.find_root(d) or "") == os.path.normcase(os.path.normpath(d)):
            self.open_repo(d)
            return
        branch, ok = QInputDialog.getText(self, t("welcome.init"), t("init.branch"), text="main")
        if ok:
            try:
                Repo.init(d, branch.strip() or "main")
            except GitError as e:
                QMessageBox.warning(self, t("welcome.init"), str(e))
                return
            self.open_repo(d)

    def settings(self):
        v = self.current()
        repo = v.repo if v else None
        name = repo.get_config("user.name") if repo else ""
        email = repo.get_config("user.email") if repo else ""
        if not repo:
            name = decode(run_git(["config", "--global", "--get", "user.name"], os.path.expanduser("~"))[1]).strip()
            email = decode(run_git(["config", "--global", "--get", "user.email"], os.path.expanduser("~"))[1]).strip()
        d = SettingsDialog(self, self.cfg, name, email)
        d.open_accounts.clicked.connect(lambda: self.accounts_dialog())
        if not d.exec():
            return
        old_lang, old_theme = self.cfg.get("language"), self.cfg.get("theme")
        d.apply_to(self.cfg)
        n, e = d.user_name.text().strip(), d.user_email.text().strip()
        home = os.path.expanduser("~")
        if n and n != name:
            run_git(["config", "--global", "user.name", n], home)
        if e and e != email:
            run_git(["config", "--global", "user.email", e], home)
        save_config(self.cfg)
        self._apply_fetch_timer()
        if self.cfg["theme"] != old_theme:
            self.set_theme(self.cfg["theme"])
        if self.cfg["language"] != old_lang:
            self.set_language(self.cfg["language"])

    def set_theme(self, key: str):
        self.cfg["theme"] = key
        save_config(self.cfg)
        self._ask_restart(t("settings.restart_theme"))

    def set_language(self, code: str):
        self.cfg["language"] = code
        save_config(self.cfg)
        self._ask_restart(t("settings.restart_lang"))

    def _ask_restart(self, msg: str):
        if QMessageBox.question(self, APP_NAME, msg) == QMessageBox.Yes:
            self.restart()

    def restart(self):
        self._save_state()
        import subprocess
        args = [sys.executable] + ([] if getattr(sys, "frozen", False) else ["-m", "gitcat"])
        env = dict(os.environ)
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        subprocess.Popen(args, env=env, cwd=os.getcwd())
        QApplication.instance().quit()

    def palette(self):
        items: list[tuple[str, Callable]] = []
        for i in range(self.menuBar().actions().__len__()):
            menu = self.menuBar().actions()[i].menu()
            if not menu:
                continue
            for a in menu.actions():
                if a.menu():
                    for sub in a.menu().actions():
                        items.append((f"{menu.title()} › {a.text()} › {sub.text()}", sub.trigger))
                elif not a.isSeparator() and a.text():
                    sc = a.shortcut().toString()
                    items.append((f"{menu.title()} › {a.text()}" + (f"    [{sc}]" if sc else ""), a.trigger))
        v = self.current()
        if v:
            for r in v.last_refs:
                if r.kind == "local" and not r.is_head:
                    items.append((f"⎇ {t('branch.checkout')}: {r.name}", lambda n=r.name: v.checkout_ref(n)))
                elif r.kind == "remote":
                    items.append((f"☁ {t('branch.checkout_tracking')}: {r.name}", lambda x=r: v.checkout_remote(x)))
                elif r.kind == "tag":
                    items.append((f"◆ {r.name}", lambda s=r.sha: v.show_commit(s)))
        for p in self.cfg.get("recent", []):
            items.append((f"📁 {os.path.basename(p)}   {p}", lambda p=p: self.open_repo(p)))
        CommandPalette(self, items).exec()

    def show_shortcuts(self):
        rows = []
        for a in self.findChildren(QAction):
            sc = a.shortcut().toString()
            if sc and a.text():
                rows.append(f"{sc:<22} {a.text()}")
        extra = ["Ctrl+Shift+P / Ctrl+P   " + t("tb.palette"), "F5                     " + t("common.refresh"),
                 "Ctrl+Enter             " + t("work.commit"), "Ctrl+Shift+Enter       " + t("work.commit_push"),
                 "Ctrl+S / Ctrl+U        " + t("work.stage") + " / " + t("work.unstage"),
                 "Ctrl+F / F3            " + t("hist.search"), "Ctrl+1..9 / Ctrl+Tab   Tabs"]
        from .dialogs.viewers import TextDialog
        TextDialog(self, t("menu.shortcuts"), "\n".join(sorted(set(rows)) + [""] + extra)).exec()

    def about(self):
        QMessageBox.about(self, APP_NAME, f"<h2>{APP_NAME} v{__version__}</h2><p>{t('welcome.tagline')}</p>"
                          f"<p>{git_version()}<br>Python {sys.version.split()[0]} · Qt {__import__('PySide6').__version__}"
                          f"</p><p><a href='https://github.com/{GITHUB_REPOSITORY}'>github.com/{GITHUB_REPOSITORY}</a></p>")

    # ================================================================ jobs
    def run_job(self, fn: Callable, ok: Optional[Callable] = None, err: Optional[Callable] = None, label: str = "",
                progress: bool = False, quiet: bool = False) -> int:
        self._jid += 1
        jid = self._jid
        self._jobs[jid] = (ok, err)
        if label and not quiet:
            self._busy[jid] = label
            self._update_busy()
        self.pool.start(Job(jid, fn, self.bridge, progress))
        if self.dock.isHidden() and label and not quiet and progress:
            self.status(label + "…")
        return jid

    def _job_progress(self, jid: int, phase: str, pct: int):
        if jid in self._busy:
            self.progress.setRange(0, 100)
            self.progress.setValue(pct)
            self.busy_label.setText(f"{self._busy[jid]} · {phase} {pct}%")

    def _job_done(self, jid: int, success: bool, res):
        ok, err = self._jobs.pop(jid, (None, None))
        if self._busy.pop(jid, None) is not None:
            self._update_busy()
        if success:
            if ok:
                ok(res)
        elif err:
            err(res)
        else:
            self.status("⚠ " + str(res)[:300])

    def _update_busy(self):
        if self._busy:
            self.progress.setRange(0, 0)
            self.progress.show()
            self.busy_label.setText("⏳ " + " · ".join(list(self._busy.values())[-2:]))
        else:
            self.progress.hide()
            self.busy_label.setText("")

    # ================================================================ feedback
    def status(self, text: str, ms: int = 6000):
        self.statusBar().showMessage(text, ms)

    def toast(self, text: str):
        self.toast_w.pop("✔  " + text)
        self.status(text)

    def _log(self, cmd: str, code: int, out: str, err: str):
        C = theme.C
        color = C["ok"] if code == 0 else C["danger"]
        stamp = time.strftime("%H:%M:%S")
        self.console.appendHtml(f"<span style='color:{C['muted']}'>{stamp}</span> "
                                f"<span style='color:{color}'>$ {cmd.replace('<', '&lt;')}</span>")
        body = (out + ("\n" if out and err else "") + err).strip()
        if body:
            self.console.appendPlainText(body[-8000:])
        if code != 0:
            self.status(f"✖ {cmd[:80]} (exit {code})")

    def show_log(self):
        self.dock.show()
        self.dock.raise_()

    # ================================================================ background tasks
    def _apply_fetch_timer(self):
        mins = int(self.cfg.get("auto_fetch_min", 10))
        if mins > 0:
            self.fetch_timer.start(mins * 60 * 1000)
        else:
            self.fetch_timer.stop()

    def _auto_fetch(self):
        for v in self.views():
            if v.repo.remotes():
                repo = v.repo
                self.run_job(lambda r=repo: r.fetch(), lambda _, v=v: v.refresh(), lambda e: None, quiet=True)

    def check_updates(self, quiet: bool):
        def ok(info):
            if info is None:
                if not quiet:
                    QMessageBox.information(self, APP_NAME, t("update.latest", v=__version__))
                return
            self._offer_update(info)

        def err(e):
            if not quiet:
                QMessageBox.warning(self, APP_NAME, t("update.failed") + f"\n{e}")
        self.run_job(lambda: updater.check_latest_release(__version__), ok, err,
                     "" if quiet else t("menu.check_updates"), quiet=quiet)

    def _offer_update(self, info: updater.ReleaseInfo):
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setText(t("update.available", v=info.version, cur=__version__))
        install = box.addButton(t("update.install"), QMessageBox.AcceptRole) if updater.can_self_update() else None
        page = box.addButton(t("update.open_page"), QMessageBox.ActionRole)
        box.addButton(t("update.later"), QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is page:
            webbrowser.open(info.html_url)
        elif install is not None and clicked is install:
            def done(target):
                QMessageBox.information(self, APP_NAME, t("update.installed", v=info.version))
                self._save_state()
                updater.launch_installed(target)
                QApplication.instance().quit()
            self.run_job(lambda p: updater.install_release(info, __version__, p), done,
                         lambda e: QMessageBox.warning(self, APP_NAME, t("update.failed") + f"\n{e}"),
                         t("update.installing"), progress=True)

    # ================================================================ drag & drop / close
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p:
                self.open_repo(p if os.path.isdir(p) else os.path.dirname(p))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.toast_w.isVisible():
            self.toast_w.move(self.centralWidget().width() - self.toast_w.width() - 24,
                              self.centralWidget().height() - self.toast_w.height() - 48)

    def _save_state(self):
        self.cfg["open_tabs"] = [v.repo.path for v in self.views()]
        self.cfg["active_tab"] = max(0, self.tabs.currentIndex())
        self.cfg["geometry"] = bytes(self.saveGeometry().toHex()).decode()
        save_config(self.cfg)

    def closeEvent(self, e):
        self._save_state()
        self._watch(None)
        self.pool.clear()
        super().closeEvent(e)
