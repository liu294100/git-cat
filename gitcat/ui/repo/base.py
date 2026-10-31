"""Shared plumbing for repository operation mixins."""
from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtWidgets import QMessageBox

from ...common.i18n import t
from ...common.system import open_in_editor
from ...core.runner import GitError

if TYPE_CHECKING:
    from ...core.repo import Repo
    from ..main_window import MainWindow


class OpsBase:
    """Requires: self.repo, self.main, self.last_refs, self.refresh(), self.show_page()."""
    repo: "Repo"
    main: "MainWindow"
    last_refs: list

    def bg(self, fn: Callable, ok: Optional[Callable] = None, err: Optional[Callable] = None, label: str = "",
           progress: bool = False) -> int:
        return self.main.run_job(fn, ok, err, label, progress)

    def op(self, fn: Callable, label: str, success: str = "", after: Optional[Callable] = None,
           progress: bool = False, force_log: bool = True):
        """Run a mutating git operation in the background, then refresh."""
        def ok(res):
            self.refresh(force_log=force_log)
            if success:
                self.main.toast(success)
            if after:
                after(res)

        def err(e):
            self.refresh(force_log=True)
            self.error(label, e)
        self.bg(fn, ok, err, label, progress)

    def error(self, title: str, e: Exception):
        msg = str(e)
        if isinstance(e, GitError) and ("CONFLICT" in msg or "fix conflicts" in msg.lower()):
            self.show_page("work")
            QMessageBox.warning(self, title, t("err.conflict") + "\n\n" + msg[-3000:])
            return
        box = QMessageBox(QMessageBox.Warning, title or t("err.title"), msg[:600], parent=self)
        if len(msg) > 600:
            box.setDetailedText(msg)
        box.exec()

    def confirm(self, text: str, title: str = "") -> bool:
        return QMessageBox.question(self, title or t("common.confirm"), text) == QMessageBox.Yes

    def local_branches(self) -> list[str]:
        return [r.name for r in self.last_refs if r.kind == "local"]

    def remote_branches(self) -> list[str]:
        return [r.name for r in self.last_refs if r.kind == "remote"]

    def remote_names(self) -> list[str]:
        return list(self.repo.remotes())

    def open_in_editor(self, path: str):
        open_in_editor(path, self.main.cfg.get("editor", ""))

    def open_url(self, url: str):
        if url:
            webbrowser.open(url)
