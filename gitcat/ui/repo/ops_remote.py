"""Fetch, pull, push and remote management."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QMessageBox

from ...common.i18n import t
from ..dialogs.git_ops import PullDialog, PushDialog, RemoteDialog
from .base import OpsBase


class RemoteOps(OpsBase):
    def fetch(self, remote: str = ""):
        self.op(lambda p: self.repo.fetch(remote, progress=p), t("tb.fetch"), t("tb.fetched"), progress=True)

    def pull(self):
        remotes = self.remote_names()
        if not remotes:
            QMessageBox.information(self, t("pull.title"), t("err.no_remote"))
            return
        up = self.repo.upstream()
        r, _, b = up.partition("/") if up else (remotes[0], "", self.repo.current_branch() or "")
        d = PullDialog(self, remotes, r, b, self.main.cfg.get("pull_rebase", False))
        if d.exec():
            rem, br, rb, au = d.remote.currentText(), d.branch.text().strip(), d.rebase.isChecked(), d.autostash.isChecked()
            self.op(lambda p: self.repo.pull(rem, br, rb, au, p), t("pull.title"), t("pull.done"), progress=True)

    def quick_pull(self):
        if not self.repo.upstream():
            self.pull()
            return
        rb = self.main.cfg.get("pull_rebase", False)
        self.op(lambda p: self.repo.do_stream("pull", "--progress", "--rebase" if rb else "--no-rebase",
                                              "--autostash", progress=p),
                t("pull.title"), t("pull.done"), progress=True)

    def push(self, local: Optional[str] = None, quick: bool = False):
        remotes = self.remote_names()
        if not remotes:
            if self.confirm(t("push.no_remote_add")):
                self.add_remote()
            return
        cur = self.repo.current_branch() or ""
        local = local or cur
        up = self.repo.upstream(local) if local else ""
        if quick and up and local == cur:
            r, _, b = up.partition("/")
            self.op(lambda p: self.repo.push(r, local, b, progress=p), t("push.title"), t("push.done"), progress=True)
            return
        d = PushDialog(self, remotes, self.local_branches(), local, up)
        if d.exec():
            r, lb, rb = d.remote.currentText(), d.local.currentText(), d.remote_branch.text().strip()
            su, f, tg, nv = d.upstream.isChecked(), d.force.isChecked(), d.tags.isChecked(), d.no_verify.isChecked()
            if f and not self.confirm(t("push.force_confirm")):
                return
            self.op(lambda p: self.repo.push(r, lb, rb, su, f, tg, nv, p), t("push.title"), t("push.done"),
                    progress=True)

    def add_remote(self):
        d = RemoteDialog(self)
        if d.exec():
            n, u = d.name.text().strip(), d.url.text().strip()
            self.op(lambda: self.repo.add_remote(n, u), t("remote.add"), after=lambda _: self.fetch(n))

    def edit_remote(self, name: str, url: str):
        d = RemoteDialog(self, name, url)
        if d.exec():
            u = d.url.text().strip()
            self.op(lambda: self.repo.set_remote_url(name, u), t("remote.edit"))

    def remove_remote(self, name: str):
        if self.confirm(t("remote.remove_confirm", name=name)):
            self.op(lambda: self.repo.remove_remote(name), t("remote.remove"))
