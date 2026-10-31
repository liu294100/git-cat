"""Working-copy operations: stage, discard, resolve, commit, clean."""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QInputDialog, QMessageBox

from ...common.i18n import t
from ...core.models import FileChange
from ...core.runner import GitError
from ..dialogs.git_ops import CleanDialog
from .base import OpsBase


class WorkingOps(OpsBase):
    def stage(self, files: list[FileChange]):
        if files:
            self._quick(lambda: self.repo.stage([f.path for f in files]))

    def stage_all(self):
        self._quick(self.repo.stage_all)

    def unstage(self, files: list[FileChange]):
        if files:
            self._quick(lambda: self.repo.unstage([f.path for f in files]))

    def unstage_all(self):
        self._quick(self.repo.unstage_all)

    def _quick(self, fn: Callable):
        try:
            fn()
        except GitError as e:
            self.error(t("err.title"), e)
        self.refresh()

    def discard(self, files: list[FileChange]):
        if not files:
            return
        names = "\n".join(f.path for f in files[:15]) + ("\n…" if len(files) > 15 else "")
        if self.confirm(t("work.discard_confirm", n=len(files)) + "\n\n" + names):
            self._quick(lambda: self.repo.discard(files))

    def resolve(self, files: list[FileChange], side: str):
        self._quick(lambda: [self.repo.checkout_side(f.path, side) for f in files])

    def mark_resolved(self, files: list[FileChange]):
        self._quick(lambda: self.repo.mark_resolved([f.path for f in files]))

    def mergetool(self, fc: FileChange):
        self.op(lambda: self.repo.mergetool(fc.path), "mergetool")

    def ignore(self, pattern: str):
        self.repo.add_to_gitignore(pattern)
        self.main.toast(t("work.ignored", p=pattern))
        self.refresh()

    def stash_files(self, files: list[FileChange]):
        msg, ok = QInputDialog.getText(self, t("stash.title"), t("common.message"))
        if ok:
            self.op(lambda: self.repo.stash_push(msg, untracked=True, paths=[f.path for f in files]), t("stash.title"))

    def commit(self, push: bool = False):
        w = self.work
        msg = w.msg.toPlainText().strip()
        amend = w.amend.isChecked()
        if not msg:
            QMessageBox.information(self, t("work.commit"), t("work.need_message"))
            w.msg.setFocus()
            return
        changes = self.repo.status()
        if any(c.conflicted for c in changes):
            QMessageBox.warning(self, t("work.commit"), t("work.has_conflicts"))
            return
        stage_all = False
        if not amend and not any(c.staged for c in changes):
            if not changes:
                QMessageBox.information(self, t("work.commit"), t("work.nothing"))
                return
            if not self.confirm(t("work.stage_all_confirm", n=len(changes))):
                return
            stage_all = True
        repo, signoff, nov = self.repo, w.signoff.isChecked(), w.noverify.isChecked()

        def work():
            if stage_all:
                repo.stage_all()
            return repo.commit(msg, amend=amend, signoff=signoff, no_verify=nov)

        def after(_):
            w.msg.clear()
            w.amend.setChecked(False)
            if push:
                self.push(quick=True)
        self.op(work, t("work.commit"), t("work.committed"), after)

    def undo_commit(self):
        if not self.repo.rev_parse("HEAD~1"):
            return
        if self.confirm(t("work.undo_confirm", msg=self.repo.last_message().split("\n")[0])):
            self.op(lambda: self.repo.reset("HEAD~1", "soft"), t("tb.undo"), t("work.undone"))

    def clean(self):
        files = self.repo.clean_preview(True, False)
        d = CleanDialog(self, files)
        if d.exec() and self.confirm(t("clean.confirm")):
            self.op(lambda: self.repo.clean(d.dirs.isChecked(), d.ignored.isChecked()), t("clean.title"))
