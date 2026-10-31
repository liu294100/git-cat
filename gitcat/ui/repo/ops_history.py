"""History operations: file history, blame, search, compare, patches, reflog."""
from __future__ import annotations

import os
import webbrowser
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import QFileDialog

from ...common.i18n import t
from ...core.models import Commit
from ...core.runner import GitError
from ...services.accounts import AccountStore
from ..dialogs.compare import CompareDialog
from ..dialogs.version_compare import VersionCompareDialog
from ..dialogs.viewers import BlameDialog, ListPickDialog, TextDialog
from .base import OpsBase


class HistoryOps(OpsBase):
    def file_history(self, path: str):
        commits = self.repo.log(path=path, max_count=1000)
        rows = [[c.short, c.subject, c.author, datetime.fromtimestamp(c.timestamp).strftime("%Y-%m-%d %H:%M")]
                for c in commits]
        dlg = ListPickDialog(self, t("file.history") + f": {path}",
                             [t("hist.col.sha"), t("hist.col.subject"), t("hist.col.author"), t("hist.col.date")],
                             rows, [(t("hist.goto"), lambda r: (dlg.accept(), self.show_commit(commits[r].sha))),
                                    (t("file.blame_at"), lambda r: self.blame(path, commits[r].sha)),
                                    ("⇄ " + t("files.cmp_worktree"),
                                     lambda r: self.compare_files(path, commits[r].sha, path, "")),
                                    ("⇄ " + t("files.cmp_prev"),
                                     lambda r: self.compare_files(path, commits[r + 1].sha if r + 1 < len(commits)
                                                                  else commits[r].sha + "^", path, commits[r].sha)),
                                    (t("file.restore_from", sha=""), lambda r: self.restore_file(commits[r].sha, path))],
                             stretch=1)
        dlg.exec()

    def blame(self, path: str, rev: str = ""):
        try:
            rows = self.repo.blame(path, rev)
        except GitError as e:
            self.error(t("file.blame"), e)
            return
        BlameDialog(self, path, rows, self.show_commit).exec()

    def deep_search(self, q: str, mode: str):
        repo = self.repo
        self.bg(lambda: repo.search_log(q, mode), self.history.show_search_results,
                lambda e: self.error(t("hist.search"), e), t("hist.searching"))

    def restore_file(self, sha: str, path: str):
        if self.confirm(t("file.restore_confirm", path=path, sha=sha[:8])):
            self.op(lambda: self.repo.restore_from(sha, path), t("file.restore_from", sha=sha[:8]))

    def save_file_at(self, sha: str, path: str):
        base = os.path.basename(path)
        root, ext = os.path.splitext(base)
        out, _ = QFileDialog.getSaveFileName(self, t("file.save_as"), os.path.join(os.path.expanduser("~"),
                                             f"{root}@{sha[:8]}{ext}"))
        if out:
            with open(out, "wb") as f:
                f.write(self.repo.file_at(sha, path))
            self.main.toast(t("common.saved", path=out))

    def show_full_diff(self, sha: str, parents: list[str]):
        data = self.repo.commit_diff(sha, parents)
        TextDialog(self, sha[:10], data.decode("utf-8", errors="replace")).exec()

    def compare(self, a: str, b: str):
        CompareDialog(self, a, b).exec()

    def format_patch(self, commits: list[Commit]):
        d = QFileDialog.getExistingDirectory(self, t("hist.patch", n=len(commits)), os.path.expanduser("~"))
        if d:
            self.op(lambda: self.repo.format_patch([c.sha for c in commits], d), t("hist.patch", n=len(commits)),
                    t("common.saved", path=d), force_log=False)

    def apply_patches(self):
        files, _ = QFileDialog.getOpenFileNames(self, t("tb.apply_patch"), os.path.expanduser("~"),
                                                "Patch (*.patch *.diff *.eml);;*")
        if files:
            self.op(lambda: self.repo.apply_mailbox(files), t("tb.apply_patch"))

    def archive(self, ref: str):
        out, _ = QFileDialog.getSaveFileName(self, t("hist.archive"),
                                             os.path.join(os.path.expanduser("~"),
                                                          f"{self.repo.name}-{ref[:12].replace('/', '-')}.zip"),
                                             "ZIP (*.zip);;tar.gz (*.tar.gz)")
        if out:
            self.op(lambda: self.repo.archive(ref, out), t("hist.archive"), t("common.saved", path=out),
                    force_log=False)

    def remote_info(self, remote: str = ""):
        """Provider-aware info for a remote (default: origin / first remote)."""
        remotes = self.repo.remotes()
        url = remotes.get(remote) if remote else (remotes.get("origin") or next(iter(remotes.values()), ""))
        return AccountStore(self.main.cfg).parse(url) if url else None

    def open_commit_web(self, sha: str):
        info = self.remote_info()
        if info:
            webbrowser.open(info.commit_url(sha))

    def open_pr(self, branch: str, remote: str = "", target: str = ""):
        info = self.remote_info(remote)
        if info:
            webbrowser.open(info.new_pr_url(branch, target))

    def open_branch_web(self, branch: str, remote: str = ""):
        info = self.remote_info(remote)
        if info:
            webbrowser.open(info.branch_url(branch))

    def default_branch(self, remote: str = "origin") -> str:
        head = self.repo.run("rev-parse", "--abbrev-ref", f"{remote}/HEAD", check=False).strip()
        return head.split("/", 1)[-1] if "/" in head else "main"

    def open_compare_web(self, base: str, head: str):
        info = self.remote_info()
        if info:
            webbrowser.open(info.compare_url(base or self.default_branch(), head))

    def compare_files(self, path: str = "", rev_a: str = "HEAD", path_b: Optional[str] = None, rev_b: str = ""):
        VersionCompareDialog(self, path, rev_a, path_b, rev_b).exec()

    def reflog(self):
        rows = self.repo.reflog()
        dlg = ListPickDialog(self, "Reflog", ["SHA", "Ref", t("common.message"), t("hist.col.date")],
                             [[r[0][:10], r[1], r[2], r[3]] for r in rows],
                             [(t("hist.goto"), lambda i: (dlg.accept(), self.show_commit(rows[i][0]))),
                              (t("branch.new_here"), lambda i: self.new_branch(rows[i][0], rows[i][2])),
                              (t("hist.reset"), lambda i: self._reset_sha(rows[i][0], rows[i][2]))])
        dlg.exec()
