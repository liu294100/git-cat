"""Accounts manager, login dialog and environment panel (GitHub, GitLab, Gitee, Gitea, Bitbucket, Azure, other)."""
from __future__ import annotations

import os
import webbrowser
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton, QRadioButton, QTabWidget, QVBoxLayout,
                               QWidget)

from ...common.config import save_config
from ...common.i18n import t
from ...core import credentials
from ...core.hosting import PROVIDER_NAMES, PROVIDERS, SSH_KEY_PAGES, TOKEN_PAGES
from ...core.runner import run_git
from ...services import accounts as acc_svc
from ...services.accounts import AUTH_BROWSER, AUTH_SSH, AUTH_TOKEN, STORE_CONFIG, STORE_HELPER, Account
from ...services.providers import client_for
from .. import theme
from .base import FormDialog

if TYPE_CHECKING:
    from ..main_window import MainWindow

PROVIDER_ICON = {"github": "🐙", "gitlab": "🦊", "gitee": "🟥", "gitea": "🍵", "bitbucket": "🪣", "azure": "🔷",
                 "generic": "🌐"}


class AccountEditDialog(FormDialog):
    def __init__(self, main: "MainWindow", acc: Optional[Account] = None, provider: str = "github",
                 host: str = "", token: str = ""):
        super().__init__(main, t("acc.edit") if acc else t("acc.add"), t("common.save"))
        self.main = main
        self.setMinimumWidth(680)
        self.acc = acc
        self.secret = token
        self.provider = QComboBox()
        for p in PROVIDERS:
            self.provider.addItem(f"{PROVIDER_ICON[p]}  {PROVIDER_NAMES[p]}", p)
        self.host = QLineEdit()
        self.host.setPlaceholderText("github.com / gitlab.example.com")
        self.form.addRow(t("acc.provider"), self.provider)
        self.form.addRow(t("acc.host"), self.host)

        # auth method
        self.auth_group = QButtonGroup(self)
        auth_row = QHBoxLayout()
        self.r_token = QRadioButton("🔑 " + t("acc.auth_token"))
        self.r_browser = QRadioButton("🌐 " + t("acc.auth_browser"))
        self.r_ssh = QRadioButton("🗝 SSH")
        for r in (self.r_token, self.r_browser, self.r_ssh):
            self.auth_group.addButton(r)
            auth_row.addWidget(r)
        auth_row.addStretch(1)
        self.form.addRow(t("acc.auth"), auth_row)

        # token block
        self.token_box = QWidget()
        tl = QHBoxLayout(self.token_box)
        tl.setContentsMargins(0, 0, 0, 0)
        self.token = QLineEdit(token)
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText(t("acc.token_hint"))
        self.b_create = QPushButton("＋ " + t("acc.create_token"))
        self.b_verify = QPushButton("✔ " + t("acc.verify"))
        tl.addWidget(self.token, 1)
        tl.addWidget(self.b_create)
        tl.addWidget(self.b_verify)
        self.form.addRow("Token", self.token_box)
        self.browser_box = QWidget()
        bl = QHBoxLayout(self.browser_box)
        bl.setContentsMargins(0, 0, 0, 0)
        self.b_browser = QPushButton("🌐 " + t("acc.browser_login"))
        self.b_browser.setObjectName("primary")
        bl.addWidget(self.b_browser)
        self.browser_note = QLabel("")
        self.browser_note.setObjectName("muted")
        self.browser_note.setWordWrap(True)
        bl.addWidget(self.browser_note, 1)
        self.form.addRow("", self.browser_box)

        # ssh block
        self.ssh_box = QWidget()
        sl = QHBoxLayout(self.ssh_box)
        sl.setContentsMargins(0, 0, 0, 0)
        self.ssh_key = QComboBox()
        self.ssh_key.setEditable(True)
        self.ssh_key.addItems(acc_svc.list_ssh_keys())
        b_gen = QPushButton(t("acc.ssh_generate"))
        b_copy = QPushButton(t("acc.ssh_copy"))
        b_page = QPushButton(t("acc.ssh_page"))
        b_test = QPushButton(t("acc.ssh_test"))
        sl.addWidget(self.ssh_key, 1)
        for b in (b_gen, b_copy, b_page, b_test):
            sl.addWidget(b)
        self.form.addRow(t("acc.ssh_key"), self.ssh_box)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.form.addRow("", self.status)
        self.username = QLineEdit()
        self.name = QLineEdit()
        self.email = QLineEdit()
        self.form.addRow(t("acc.username"), self.username)
        self.form.addRow(t("settings.user_name"), self.name)
        self.form.addRow(t("settings.user_email"), self.email)
        self.storage = QComboBox()
        self.storage.addItem("🔒 " + t("acc.store_helper"), STORE_HELPER)
        self.storage.addItem("⚠ " + t("acc.store_config"), STORE_CONFIG)
        self.form.addRow(t("acc.storage"), self.storage)
        self.default = QCheckBox(t("acc.default"))
        self.form.addRow("", self.default)

        # initial values
        self.avatar = ""
        if acc:
            self.provider.setCurrentIndex(max(0, self.provider.findData(acc.provider)))
            self.host.setText(acc.host)
            self.username.setText(acc.username)
            self.name.setText(acc.name)
            self.email.setText(acc.email)
            self.avatar = acc.avatar
            self.default.setChecked(acc.default)
            self.storage.setCurrentIndex(max(0, self.storage.findData(acc.storage)))
            {AUTH_TOKEN: self.r_token, AUTH_BROWSER: self.r_browser, AUTH_SSH: self.r_ssh}[acc.auth].setChecked(True)
            if acc.ssh_key:
                self.ssh_key.setCurrentText(acc.ssh_key)
        else:
            self.provider.setCurrentIndex(max(0, self.provider.findData(provider)))
            self.host.setText(host or acc_svc.default_host(provider))
            self.r_token.setChecked(True)
            self.default.setChecked(True)
        self.provider.currentIndexChanged.connect(self._provider_changed)
        for r in (self.r_token, self.r_browser, self.r_ssh):
            r.toggled.connect(lambda _: self._mode())
        self.b_create.clicked.connect(lambda: self._open_page(TOKEN_PAGES))
        self.b_verify.clicked.connect(self._verify)
        self.b_browser.clicked.connect(self._browser_login)
        b_gen.clicked.connect(self._gen_key)
        b_copy.clicked.connect(self._copy_key)
        b_page.clicked.connect(lambda: self._open_page(SSH_KEY_PAGES))
        b_test.clicked.connect(self._test_ssh)
        self.validate(lambda: None if self.host.text().strip() else t("acc.need_host"))
        self.validate(self._check_secret)
        self._mode()
        self.finish()
        if token and not acc:
            self._verify()

    # ---------------------------------------------------------------- helpers
    @property
    def prov(self) -> str:
        return self.provider.currentData()

    @property
    def auth(self) -> str:
        return AUTH_SSH if self.r_ssh.isChecked() else (AUTH_BROWSER if self.r_browser.isChecked() else AUTH_TOKEN)

    def _provider_changed(self):
        self.host.setText(acc_svc.default_host(self.prov))
        self._mode()

    def _mode(self):
        a = self.auth
        for box, on in ((self.token_box, a == AUTH_TOKEN), (self.browser_box, a == AUTH_BROWSER),
                        (self.ssh_box, a == AUTH_SSH)):
            self.form.setRowVisible(box, on)  # hides the label too
        self.storage.setEnabled(a == AUTH_TOKEN)
        gcm = credentials.has_manager()
        self.b_browser.setEnabled(gcm)
        self.browser_note.setText(t("acc.browser_ok") if gcm else t("acc.browser_no_gcm"))
        self.b_create.setEnabled(bool(TOKEN_PAGES.get(self.prov)))

    def _open_page(self, pages: dict):
        url = pages.get(self.prov, "").format(host=self.host.text().strip() or acc_svc.default_host(self.prov))
        if url:
            webbrowser.open(url)

    def _set_status(self, ok: bool, text: str):
        self.status.setText(("✅ " if ok else "⚠ ") + text)
        self.status.setStyleSheet(f"color: {theme.C['ok' if ok else 'danger']};")

    def _apply_user(self, u: dict):
        self.username.setText(self.username.text() or u.get("login", ""))
        self.name.setText(self.name.text() or u.get("name", ""))
        self.email.setText(self.email.text() or u.get("email", ""))
        self.avatar = u.get("avatar", "")
        self._set_status(True, t("acc.verified", user=u.get("login") or u.get("name", "")))

    def _verify(self):
        token = self.token.text().strip() or self.secret
        host, prov, user = self.host.text().strip(), self.prov, self.username.text().strip()
        if not token:
            self._set_status(False, t("acc.need_token"))
            return
        if prov == "generic":
            self._set_status(True, t("acc.generic_note"))
            return
        self.status.setText("⏳ " + t("acc.verifying"))
        self.main.run_job(lambda: client_for(prov, host, token, user).current_user(), self._apply_user,
                          lambda e: self._set_status(False, str(e)), "")

    def _browser_login(self):
        host, user = self.host.text().strip(), self.username.text().strip()
        self.status.setText("⏳ " + t("acc.browser_wait"))
        prov = self.prov

        def work():
            login, secret = credentials.browser_login(host, user)
            u = {}
            if prov != "generic":
                try:
                    u = client_for(prov, host, secret, login).current_user()
                except Exception:  # noqa: BLE001 - token may not be API-capable, still valid for git
                    u = {}
            return login, secret, u

        def done(res):
            login, secret, u = res
            self.secret = secret
            self.username.setText(login or self.username.text())
            if u:
                self._apply_user(u)
            else:
                self._set_status(True, t("acc.verified", user=login))
        self.main.run_job(work, done, lambda e: self._set_status(False, str(e)), t("acc.browser_login"))

    def _gen_key(self):
        name, ok = QInputDialog.getText(self, t("acc.ssh_generate"), t("acc.ssh_name"),
                                        text=f"id_ed25519_{self.prov}")
        if not ok or not name.strip():
            return
        try:
            path = acc_svc.generate_ssh_key(self.email.text().strip(), name.strip())
        except (FileExistsError, RuntimeError) as e:
            QMessageBox.warning(self, "SSH", str(e))
            return
        self.ssh_key.addItem(path)
        self.ssh_key.setCurrentText(path)
        self._copy_key()
        self._set_status(True, t("acc.ssh_generated"))

    def _copy_key(self):
        pub = acc_svc.public_key(self.ssh_key.currentText().strip())
        if pub:
            QApplication.clipboard().setText(pub)
            self._set_status(True, t("acc.ssh_copied"))
        else:
            self._set_status(False, t("acc.ssh_no_pub"))

    def _test_ssh(self):
        host, key = self.host.text().strip(), self.ssh_key.currentText().strip()
        self.status.setText("⏳ " + t("acc.verifying"))
        self.main.run_job(lambda: acc_svc.test_ssh(host, key), lambda r: self._set_status(r[0], r[1][:300]),
                          lambda e: self._set_status(False, str(e)), "")

    def _check_secret(self) -> Optional[str]:
        if self.auth == AUTH_TOKEN and not (self.token.text().strip() or self.secret or self.acc):
            return t("acc.need_token")
        if self.auth == AUTH_SSH and not self.ssh_key.currentText().strip():
            return t("acc.need_key")
        if self.auth == AUTH_BROWSER and not (self.secret or self.acc):
            return t("acc.need_browser")
        return None

    def result_account(self) -> tuple[Account, str]:
        a = self.acc or Account(provider=self.prov, host="")
        a.provider = self.prov
        a.host = self.host.text().strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
        a.username, a.name, a.email = self.username.text().strip(), self.name.text().strip(), self.email.text().strip()
        a.auth, a.avatar, a.default = self.auth, self.avatar, self.default.isChecked()
        a.storage = self.storage.currentData() if a.auth == AUTH_TOKEN else STORE_HELPER
        a.ssh_key = self.ssh_key.currentText().strip() if a.auth == AUTH_SSH else ""
        secret = self.token.text().strip() if a.auth == AUTH_TOKEN else ""
        return a, secret


class AccountsDialog(QDialog):
    def __init__(self, main: "MainWindow"):
        super().__init__(main)
        self.main = main
        self.store = acc_svc.AccountStore(main.cfg)
        self.setWindowTitle("👤 " + t("acc.title"))
        self.resize(900, 640)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        tabs = QTabWidget()
        lay.addWidget(tabs, 1)

        page = QWidget()
        pl = QVBoxLayout(page)
        self.list = QListWidget()
        pl.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.b_add = QPushButton("＋ " + t("acc.add"))
        self.b_add.setObjectName("primary")
        self.b_edit = QPushButton(t("acc.edit"))
        self.b_verify = QPushButton("✔ " + t("acc.verify"))
        self.b_default = QPushButton("★ " + t("acc.make_default"))
        self.b_bind = QPushButton("📌 " + t("acc.use_for_repo"))
        self.b_logout = QPushButton("⎋ " + t("acc.logout"))
        self.b_logout.setObjectName("danger")
        for b in (self.b_add, self.b_edit, self.b_verify, self.b_default, self.b_bind):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self.b_logout)
        pl.addLayout(row)
        self.note = QLabel("")
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        pl.addWidget(self.note)
        tabs.addTab(page, "👤 " + t("acc.accounts"))

        self.env_page = QWidget()
        tabs.addTab(self.env_page, "🧭 " + t("acc.environment"))
        tabs.currentChanged.connect(lambda i: i == 1 and self._load_env())

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(t("common.close"))
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.b_add.clicked.connect(lambda: self.edit(None))
        self.b_edit.clicked.connect(lambda: self.current() and self.edit(self.current()))
        self.list.itemDoubleClicked.connect(lambda _: self.current() and self.edit(self.current()))
        self.b_verify.clicked.connect(self.verify)
        self.b_default.clicked.connect(self.make_default)
        self.b_bind.clicked.connect(self.bind)
        self.b_logout.clicked.connect(self.logout)
        self.b_bind.setEnabled(main.current() is not None)
        self.fill()

    # ---------------------------------------------------------------- list
    def current(self) -> Optional[Account]:
        it = self.list.currentItem()
        return self.store.get(it.data(Qt.UserRole)) if it else None

    def fill(self):
        cur = self.current()
        self.list.clear()
        accounts = self.store.all()
        for a in accounts:
            auth = {AUTH_TOKEN: "Token", AUTH_BROWSER: "OAuth / GCM", AUTH_SSH: "SSH"}[a.auth]
            store = "" if a.auth == AUTH_SSH else (" · 🔒" if a.storage == STORE_HELPER else " · ⚠ config")
            it = QListWidgetItem(f"{PROVIDER_ICON.get(a.provider, '🌐')}  {'★ ' if a.default else ''}{a.label}\n"
                                 f"      {PROVIDER_NAMES.get(a.provider, a.provider)} · {auth}{store}"
                                 + (f" · {a.name} <{a.email}>" if a.email else ""))
            it.setData(Qt.UserRole, a.id)
            it.setForeground(theme.color("text"))
            it.setToolTip(a.ssh_key or a.host)
            it.setBackground(theme.color("panel"))
            self.list.addItem(it)
            if cur and cur.id == a.id:
                self.list.setCurrentItem(it)
        if accounts and not self.list.currentItem():
            self.list.setCurrentRow(0)
        if not accounts:
            self.note.setText("💡 " + t("acc.empty"))
        else:
            self.note.setText(t("acc.note"))
        for b in (self.b_edit, self.b_verify, self.b_default, self.b_logout):
            b.setEnabled(bool(accounts))

    def _persist(self):
        save_config(self.main.cfg)
        self.fill()
        self.main.accounts_changed()

    def edit(self, acc: Optional[Account], **preset):
        d = AccountEditDialog(self.main, acc, **preset)
        if not d.exec():
            return
        a, secret = d.result_account()
        if a.auth == AUTH_TOKEN and a.storage == STORE_HELPER and secret and not credentials.helpers():
            helper = credentials.recommended_helper()
            btn = QMessageBox.question(self, t("acc.title"), t("acc.no_helper", helper=helper),
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if btn == QMessageBox.Cancel:
                return
            if btn == QMessageBox.Yes:
                try:
                    credentials.enable_helper(helper)
                except RuntimeError as e:
                    QMessageBox.warning(self, t("acc.title"), str(e))
                    return
            else:
                a.storage = STORE_CONFIG
        try:
            self.store.save(a, secret)
        except RuntimeError as e:
            QMessageBox.warning(self, t("acc.title"), str(e))
            return
        self._persist()
        self.main.toast(t("acc.saved", who=a.label))

    def verify(self):
        a = self.current()
        if not a:
            return
        if a.auth == AUTH_SSH:
            self.main.run_job(lambda: acc_svc.test_ssh(a.host, a.ssh_key),
                              lambda r: QMessageBox.information(self, "SSH", ("✅ " if r[0] else "⚠ ") + r[1][:800]),
                              None, t("acc.verifying"))
            return

        def work():
            token, user, src = self.store.token_for(a.provider, a.host, a.username)
            if not token:
                raise RuntimeError(t("acc.need_token"))
            return client_for(a.provider, a.host, token, user).current_user(), src
        self.main.run_job(work, lambda r: QMessageBox.information(
            self, t("acc.verify"), t("acc.verified", user=r[0].get("login") or r[0].get("name")) + f"\n({r[1]})"),
            lambda e: QMessageBox.warning(self, t("acc.verify"), str(e)), t("acc.verifying"))

    def make_default(self):
        a = self.current()
        if a:
            self.store.set_default(a.id)
            self._persist()

    def bind(self):
        a, rv = self.current(), self.main.current()
        if not a or not rv:
            return
        if not QMessageBox.question(self, t("acc.use_for_repo"), t("acc.bind_confirm", who=a.label,
                                                                      repo=rv.repo.name)) == QMessageBox.Yes:
            return
        try:
            done = acc_svc.apply_to_repo(rv.repo, a)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, t("acc.use_for_repo"), str(e))
            return
        QMessageBox.information(self, t("acc.use_for_repo"), "\n".join(done) or t("acc.bound"))
        rv.refresh()
        self.main.accounts_changed()

    def logout(self):
        a = self.current()
        if a and QMessageBox.question(self, t("acc.logout"), t("acc.logout_confirm", who=a.label)) == QMessageBox.Yes:
            self.store.logout(a.id)
            self._persist()

    # ---------------------------------------------------------------- environment
    def _load_env(self):
        if self.env_page.layout():
            return
        lay = QVBoxLayout(self.env_page)
        wait = QLabel("⏳ " + t("acc.env_loading"))
        lay.addWidget(wait)
        self.main.run_job(acc_svc.detect_environment, lambda env: self._show_env(env, wait), None, "")

    def _show_env(self, env: acc_svc.Environment, wait: QLabel):
        lay = self.env_page.layout()
        wait.deleteLater()
        g1 = QGroupBox("Git")
        f1 = QFormLayout(g1)
        f1.addRow(t("acc.git_version"), QLabel(env.git_version or "—"))
        name, email = QLineEdit(env.user_name), QLineEdit(env.user_email)
        save_id = QPushButton(t("common.save"))
        idr = QHBoxLayout()
        idr.addWidget(name)
        idr.addWidget(email)
        idr.addWidget(save_id)
        f1.addRow(t("settings.identity"), idr)

        def save_identity():
            home = os.path.expanduser("~")
            for k, v in (("user.name", name.text().strip()), ("user.email", email.text().strip())):
                if v:
                    run_git(["config", "--global", k, v], home)
            self.main.toast(t("acc.identity_saved"))
        save_id.clicked.connect(save_identity)
        helpers = ", ".join(env.helpers) or "—"
        hr = QHBoxLayout()
        hr.addWidget(QLabel(helpers), 1)
        if not env.helpers:
            en = QPushButton(t("acc.enable_helper", helper=credentials.recommended_helper()))
            en.clicked.connect(lambda: (credentials.enable_helper(credentials.recommended_helper()),
                                        self.main.toast(t("acc.helper_enabled"))))
            hr.addWidget(en)
        f1.addRow(t("acc.helpers"), hr)
        lay.addWidget(g1)

        g2 = QGroupBox(t("acc.detected"))
        v2 = QVBoxLayout(g2)
        found = False
        for prov, var in env.env_tokens:
            found = True
            r = QHBoxLayout()
            r.addWidget(QLabel(f"{PROVIDER_ICON.get(prov, '🌐')} {PROVIDER_NAMES[prov]} · ${var}"), 1)
            b = QPushButton(t("acc.import"))
            b.clicked.connect(lambda _=False, p=prov, v=var: self.edit(None, provider=p, host=acc_svc.default_host(p),
                                                                       token=os.environ.get(v, "")))
            r.addWidget(b)
            v2.addLayout(r)
        for prov, host in env.cli_logins:
            found = True
            r = QHBoxLayout()
            r.addWidget(QLabel(f"{PROVIDER_ICON.get(prov, '🌐')} {'gh' if prov == 'github' else 'glab'} CLI · {host}"), 1)
            b = QPushButton(t("acc.import"))
            b.clicked.connect(lambda _=False, p=prov, h=host: self.edit(None, provider=p, host=h,
                                                                        token=acc_svc.import_cli(p, h)))
            r.addWidget(b)
            v2.addLayout(r)
        if not found:
            v2.addWidget(QLabel(t("acc.nothing_detected")))
        lay.addWidget(g2)

        g3 = QGroupBox(t("acc.ssh_keys"))
        v3 = QVBoxLayout(g3)
        for key in env.ssh_keys:
            r = QHBoxLayout()
            r.addWidget(QLabel("🗝 " + key), 1)
            b = QPushButton(t("acc.ssh_copy"))
            b.clicked.connect(lambda _=False, k=key: (QApplication.clipboard().setText(acc_svc.public_key(k)),
                                                       self.main.toast(t("acc.ssh_copied"))))
            r.addWidget(b)
            v3.addLayout(r)
        if not env.ssh_keys:
            v3.addWidget(QLabel(t("acc.no_ssh")))
        lay.addWidget(g3)
        lay.addStretch(1)
