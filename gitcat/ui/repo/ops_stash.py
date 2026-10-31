"""Stash, worktree and miscellaneous repository operations."""
from __future__ import annotations

import os

from PySide6.QtWidgets import QInputDialog

from ...common.i18n import t
from ...core.models import Worktree
from ..dialogs.git_ops import StashDialog, WorktreeDialog
from .base import OpsBase


class StashOps(OpsBase):
    def stash(self):
        d = StashDialog(self)
        if d.exec():
            m, u, k, s = d.message.text().strip(), d.untracked.isChecked(), d.keep_index.isChecked(), \
                d.staged_only.isChecked()
            self.op(lambda: self.repo.stash_push(m, u, k, s), t("stash.title"), t("stash.done"))

    def stash_pop_latest(self):
        if self.repo.stashes():
            self.stash_apply("stash@{0}", True)

    def stash_apply(self, ref: str, pop: bool, index: bool = False):
        self.op(lambda: self.repo.stash_apply(ref, pop, index), t("stash.pop") if pop else t("stash.apply"))

    def stash_drop(self, ref: str):
        if self.confirm(t("stash.drop_confirm", ref=ref)):
            self.op(lambda: self.repo.stash_drop(ref), t("stash.drop"))

    def stash_branch(self, ref: str):
        name, ok = QInputDialog.getText(self, t("stash.to_branch"), t("branch.name"))
        if ok and name.strip():
            self.op(lambda: self.repo.stash_branch(name.strip(), ref), t("stash.to_branch"))

    def add_worktree(self):
        d = WorktreeDialog(self, self.repo.path, self.local_branches())
        if d.exec():
            b, p, nb = d.branch.currentText().strip(), d.path.text().strip(), d.new_branch.isChecked()
            self.op(lambda: self.repo.add_worktree(p, b, nb), t("wt.add"), after=lambda _: self.main.open_repo(p))

    def remove_worktree(self, w: Worktree):
        if self.confirm(t("wt.remove_confirm", path=w.path)):
            def err(e):
                if self.confirm(t("wt.force_remove") + "\n\n" + str(e)):
                    self.op(lambda: self.repo.remove_worktree(w.path, True), t("wt.remove"))
            self.bg(lambda: self.repo.remove_worktree(w.path), lambda _: self.refresh(), err, t("wt.remove"))

    def run_custom(self):
        cmd, ok = QInputDialog.getText(self, t("tb.custom"), t("tb.custom_hint"), text="git ")
        if ok and cmd.strip() and cmd.strip() != "git":
            self.op(lambda: self.repo.custom(cmd), cmd, after=lambda out: out and self.main.show_log())

    def edit_gitignore(self):
        p = os.path.join(self.repo.path, ".gitignore")
        if not os.path.exists(p):
            open(p, "a", encoding="utf-8").close()
        self.open_in_editor(p)

    def gc(self):
        self.op(self.repo.gc, "git gc", t("tb.gc_done"), force_log=False)
