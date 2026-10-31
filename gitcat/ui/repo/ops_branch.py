"""Branch, merge, rebase, cherry-pick, reset and bisect operations."""
from __future__ import annotations

import tempfile

from PySide6.QtWidgets import QInputDialog, QMessageBox

from ...common.i18n import t
from ...core.models import Commit, Ref
from ...core.validation import valid_ref_name
from ..dialogs.base import FormDialog, editable_combo
from ..dialogs.git_ops import BranchDialog, MergeDialog, ResetDialog
from ..dialogs.rebase import InteractiveRebaseDialog
from .base import OpsBase


class BranchOps(OpsBase):
    def checkout_ref(self, name: str, detached: bool = False):
        self.op(lambda: self.repo.checkout(name), t("branch.checkout"), t("branch.checked_out", name=name))

    def checkout_commit(self, c: Commit):
        names = [r.name for r in self.last_refs if r.kind == "local" and r.sha == c.sha]
        if names:
            self.checkout_ref(names[0])
            return
        remotes = [r for r in self.last_refs if r.kind == "remote" and r.sha == c.sha]
        if remotes:
            self.checkout_remote(remotes[0])
            return
        if self.confirm(t("hist.detached_confirm", sha=c.short)):
            self.checkout_ref(c.sha)

    def checkout_remote(self, r: Ref):
        local = r.branch_on_remote
        if local in self.local_branches():
            if self.confirm(t("branch.exists_checkout", name=local)):
                self.checkout_ref(local)
            return
        name, ok = QInputDialog.getText(self, t("branch.checkout_tracking"), t("branch.name"), text=local)
        if ok and name.strip():
            self.op(lambda: self.repo.checkout_tracking(r.name, name.strip()), t("branch.checkout_tracking"),
                    t("branch.checked_out", name=name.strip()))

    def new_branch(self, start: str = "HEAD", label: str = ""):
        d = BranchDialog(self, start, label)
        if d.exec():
            name = d.name.text().strip()
            self.op(lambda: self.repo.create_branch(name, d.start.text().strip(), d.checkout.isChecked()),
                    t("branch.new"), t("branch.created", name=name))

    def rename_branch(self, old: str):
        new, ok = QInputDialog.getText(self, t("branch.rename"), t("branch.name"), text=old)
        if ok and new.strip() and new.strip() != old:
            err = valid_ref_name(new.strip())
            if err:
                QMessageBox.warning(self, t("branch.rename"), err)
                return
            self.op(lambda: self.repo.rename_branch(old, new.strip()), t("branch.rename"))

    def delete_branch(self, r: Ref):
        if not self.confirm(t("branch.delete_confirm", name=r.name)):
            return

        def err(e):
            if "not fully merged" in str(e) and self.confirm(t("branch.force_delete", name=r.name)):
                self.op(lambda: self.repo.delete_branch(r.name, True), t("branch.delete"))
            else:
                self.error(t("branch.delete"), e)
        self.bg(lambda: self.repo.delete_branch(r.name), lambda _: self.refresh(force_log=True), err, t("branch.delete"))

    def delete_remote_branch(self, r: Ref):
        if self.confirm(t("branch.delete_remote_confirm", name=r.name)):
            self.op(lambda: self.repo.delete_remote_branch(r.remote, r.branch_on_remote), t("branch.delete_remote"),
                    progress=False)

    def set_upstream(self, branch: str):
        d = FormDialog(self, t("branch.set_upstream"))
        cb = editable_combo(self.remote_branches(), self.repo.upstream(branch) or f"origin/{branch}")
        d.form.addRow(t("common.branch"), cb)
        d.finish()
        if d.exec():
            self.op(lambda: self.repo.set_upstream(branch, cb.currentText().strip()), t("branch.set_upstream"))

    def merge(self, preset: str = ""):
        cur = self.repo.current_branch() or "HEAD"
        cands = [b for b in self.local_branches() if b != cur] + self.remote_branches()
        d = MergeDialog(self, cur, cands, preset)
        if not d.exec():
            return
        mode = d.mode.currentIndex()
        src = d.source.currentText().strip()
        msg, nc = d.message.text().strip(), d.no_commit.isChecked()
        self.op(lambda: self.repo.merge(src, no_ff=mode == 1, ff_only=mode == 2, squash=mode == 3, no_commit=nc,
                                        message=msg), t("merge.ok"), t("merge.done", src=src))

    def rebase_onto(self, ref: str, label: str):
        cur = self.repo.current_branch() or "HEAD"
        if self.confirm(t("branch.rebase_confirm", cur=cur, onto=label)):
            self.op(lambda: self.repo.rebase(ref), "rebase", t("branch.rebased"))

    def interactive_rebase(self, c: Commit):
        base = c.parents[0] if c.parents else ""
        if not base:
            QMessageBox.information(self, t("irebase.title"), t("irebase.root"))
            return
        commits = self.repo.rebase_commits(base)
        if not commits:
            QMessageBox.information(self, t("irebase.title"), t("irebase.empty"))
            return
        d = InteractiveRebaseDialog(self, commits, c.short + "^")
        if d.exec():
            plan = d.plan()
            work = tempfile.mkdtemp(prefix="gitcat-rebase-")
            self.op(lambda: self.repo.rebase_interactive(base, plan, work), t("irebase.title"), t("branch.rebased"))

    def cherry_pick(self, commits: list[Commit]):
        shas = [c.sha for c in reversed(commits)]
        merge = any(len(c.parents) > 1 for c in commits)
        if self.confirm(t("hist.cherry_confirm", n=len(shas))):
            self.op(lambda: self.repo.cherry_pick(shas, mainline=merge), "cherry-pick", t("hist.picked"))

    def revert(self, c: Commit):
        if self.confirm(t("hist.revert_confirm", sha=c.short, msg=c.subject)):
            self.op(lambda: self.repo.revert(c.sha, mainline=len(c.parents) > 1), "revert")

    def reset_to(self, c: Commit):
        self._reset_sha(c.sha, c.subject)

    def _reset_sha(self, sha: str, label: str):
        d = ResetDialog(self, self.repo.current_branch() or "", sha, label)
        if d.exec():
            mode = d.mode
            if mode == "hard" and not self.confirm(t("reset.hard_confirm")):
                return
            self.op(lambda: self.repo.reset(sha, mode), "reset")

    def bisect_start(self, good: str):
        if self.confirm(t("bisect.start_confirm", sha=good[:8])):
            self.op(lambda: self.repo.bisect_start("HEAD", good), "bisect")

    def bisect(self, verdict: str):
        fn = self.repo.bisect_reset if verdict == "reset" else (lambda: self.repo.bisect_mark(verdict))

        def after(out):
            if out and "is the first bad commit" in out:
                QMessageBox.information(self, "Bisect", out[:2000])
            elif out:
                self.main.status(out.splitlines()[0][:200])
        self.op(fn, "bisect", after=after)

    def continue_op(self):
        st = self.repo.state()
        if st.bisecting and not st.kind:
            return
        self.op(lambda: self.repo.continue_op(st), t("banner.continue"))

    def abort_op(self):
        st = self.repo.state()
        if self.confirm(t("banner.abort_confirm")):
            self.op(lambda: self.repo.abort_op(st), t("banner.abort"))

    def skip_op(self):
        st = self.repo.state()
        self.op(lambda: self.repo.skip_op(st), t("banner.skip"))
