"""Tag management and the one-click release flow."""
from __future__ import annotations

import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QInputDialog, QMessageBox

from ...common.i18n import t
from ...services import release as rel
from ..dialogs.git_ops import TagDialog
from ..dialogs.release import ReleaseDialog
from .base import OpsBase


class ReleaseOps(OpsBase):
    def new_tag(self, target: str = "HEAD", label: str = ""):
        latest = self.repo.latest_version_tag()
        suggestion = ""
        if latest:
            suggestion = ("v" if latest.startswith("v") else "") + rel.bump(latest.lstrip("v"), "patch")
        d = TagDialog(self, target, label, self.remote_names(), suggestion)
        if not d.exec():
            return
        name, tgt = d.name.text().strip(), d.target.text().strip() or "HEAD"
        msg, force = d.message.toPlainText().strip(), d.force.isChecked()
        push, remote = d.push.isChecked(), d.remote.currentText()
        repo = self.repo

        def work(progress):
            out = repo.create_tag(name, tgt, msg, force)
            if push and remote:
                out += "\n" + repo.push_refs(remote, [("+" if force else "") + f"refs/tags/{name}"], progress)
            return out
        self.op(work, t("tag.new"), t("tag.created", name=name), progress=True)

    def push_tag(self, name: str):
        remotes = self.remote_names()
        if not remotes:
            QMessageBox.information(self, t("tag.push"), t("err.no_remote"))
            return
        remote, ok = remotes[0], True
        if len(remotes) > 1:
            remote, ok = QInputDialog.getItem(self, t("tag.push"), t("common.remote"), remotes, 0, False)
        if ok and remote:
            self.op(lambda p: self.repo.push_refs(remote, [f"refs/tags/{name}"], p), t("tag.push"),
                    t("tag.pushed", name=name), progress=True)

    def push_all_tags(self):
        remotes = self.remote_names()
        if remotes:
            self.op(lambda p: self.repo.push(remotes[0], "", tags=True, progress=p), t("tag.push_all"),
                    t("tag.pushed", name="*"), progress=True)

    def delete_tag(self, name: str, remote: bool):
        if remote:
            remotes = self.remote_names()
            if not remotes or not self.confirm(t("tag.delete_remote_confirm", name=name, remote=remotes[0])):
                return
            self.op(lambda: self.repo.delete_remote_tag(remotes[0], name), t("tag.delete_remote"))
        elif self.confirm(t("tag.delete_confirm", name=name)):
            self.op(lambda: self.repo.delete_tag(name), t("tag.delete"))

    def release(self):
        repo = self.repo
        if repo.status() and not self.confirm(t("release.dirty")):
            return
        latest = repo.latest_version_tag()
        files = rel.detect_version_files(repo.path)
        notes = rel.notes_from_subjects(repo.log_since(latest))
        has_wf = os.path.isdir(os.path.join(repo.path, ".github", "workflows"))
        d = ReleaseDialog(self, latest, files, notes, self.remote_names(), repo.current_branch() or "", has_wf)
        if not d.exec():
            return
        tag, version = d.tag, d.tag.lstrip("v")
        chosen, notes = d.selected_files(), d.notes.toPlainText().strip()
        changelog, push, remote = d.changelog.isChecked(), d.push.isChecked(), d.remote.currentText()
        branch = repo.current_branch()
        if tag in [r.name for r in self.last_refs if r.kind == "tag"]:
            QMessageBox.warning(self, t("release.title"), t("release.tag_exists", tag=tag))
            return

        def work(progress):
            touched = []
            for vf in chosen:
                if rel.write_version(repo.path, vf, version):
                    touched.append(vf.path)
            if changelog:
                touched.append(rel.prepend_changelog(repo.path, tag, notes or tag))
            if touched:
                repo.stage(touched)
                repo.commit(f"Release {tag}")
            repo.create_tag(tag, "HEAD", f"Release {tag}\n\n{notes}".strip())
            if push and remote:
                specs = ([f"refs/heads/{branch}:refs/heads/{branch}"] if branch else []) + [f"refs/tags/{tag}"]
                repo.push_refs(remote, specs, progress)
            return tag

        def after(_):
            if push and remote:
                self.show_page("actions")
                QTimer.singleShot(4000, self.actions.reload)
        self.op(work, t("release.title"), t("release.done", tag=tag), after, progress=True)
