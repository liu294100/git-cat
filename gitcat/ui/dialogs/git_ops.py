"""Dialogs that collect parameters for git operations."""
from __future__ import annotations

import os

from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialogButtonBox, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QPlainTextEdit, QPushButton, QRadioButton, QSpinBox)

from ...common.i18n import t
from ...core.validation import valid_ref_name
from .base import FormDialog, editable_combo


class BranchDialog(FormDialog):
    def __init__(self, parent, start: str = "HEAD", start_label: str = ""):
        super().__init__(parent, t("branch.new"), t("common.create"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("feature/awesome")
        self.start = QLineEdit(start)
        self.checkout = QCheckBox(t("branch.checkout_after"))
        self.checkout.setChecked(True)
        self.form.addRow(t("branch.name"), self.name)
        self.form.addRow(t("branch.start"), self.start)
        if start_label:
            lb = QLabel(start_label)
            lb.setObjectName("muted")
            self.form.addRow("", lb)
        self.form.addRow("", self.checkout)
        self.validate(lambda: valid_ref_name(self.name.text().strip()))
        self.finish()


class TagDialog(FormDialog):
    def __init__(self, parent, target: str, label: str, remotes: list[str], suggestion: str = ""):
        super().__init__(parent, t("tag.new"), t("common.create"))
        self.name = QLineEdit(suggestion)
        self.name.setPlaceholderText("v1.0.0")
        self.target = QLineEdit(target)
        self.message = QPlainTextEdit()
        self.message.setPlaceholderText(t("tag.message_hint"))
        self.message.setFixedHeight(90)
        self.force = QCheckBox(t("tag.force"))
        self.push = QCheckBox(t("tag.push_after"))
        self.remote = QComboBox()
        self.remote.addItems(remotes)
        self.push.setChecked(bool(remotes))
        self.push.setEnabled(bool(remotes))
        row = QHBoxLayout()
        row.addWidget(self.push)
        row.addWidget(self.remote, 1)
        self.form.addRow(t("tag.name"), self.name)
        self.form.addRow(t("tag.target"), self.target)
        if label:
            lb = QLabel(label)
            lb.setObjectName("muted")
            self.form.addRow("", lb)
        self.form.addRow(t("tag.message"), self.message)
        self.form.addRow("", self.force)
        self.form.addRow("", row)
        self.validate(lambda: valid_ref_name(self.name.text().strip()))
        self.finish()


class MergeDialog(FormDialog):
    def __init__(self, parent, current: str, candidates: list[str], preset: str = ""):
        super().__init__(parent, t("merge.title", branch=current), t("merge.ok"))
        self.source = editable_combo(candidates, preset)
        self.mode = QComboBox()
        self.mode.addItems([t("merge.mode.default"), t("merge.mode.no_ff"), t("merge.mode.ff_only"),
                            t("merge.mode.squash")])
        self.no_commit = QCheckBox(t("merge.no_commit"))
        self.message = QLineEdit()
        self.message.setPlaceholderText(t("merge.message_hint"))
        self.form.addRow(t("merge.source"), self.source)
        self.form.addRow(t("merge.mode"), self.mode)
        self.form.addRow(t("merge.message"), self.message)
        self.form.addRow("", self.no_commit)
        self.validate(lambda: None if self.source.currentText().strip() else t("err.pick_branch"))
        self.finish()


class PushDialog(FormDialog):
    def __init__(self, parent, remotes: list[str], locals_: list[str], current: str, upstream: str):
        super().__init__(parent, t("push.title"), t("push.ok"))
        up_remote, _, up_branch = upstream.partition("/") if upstream else ("", "", "")
        self.remote = QComboBox()
        self.remote.addItems(remotes)
        if up_remote in remotes:
            self.remote.setCurrentText(up_remote)
        self.local = QComboBox()
        self.local.addItems(locals_)
        if current:
            self.local.setCurrentText(current)
        self.remote_branch = QLineEdit(up_branch or current)
        self.local.currentTextChanged.connect(self.remote_branch.setText)
        self.upstream = QCheckBox(t("push.set_upstream"))
        self.upstream.setChecked(not upstream)
        self.force = QCheckBox(t("push.force"))
        self.tags = QCheckBox(t("push.tags"))
        self.no_verify = QCheckBox(t("push.no_verify"))
        self.form.addRow(t("common.remote"), self.remote)
        self.form.addRow(t("push.local"), self.local)
        self.form.addRow(t("push.remote_branch"), self.remote_branch)
        for w in (self.upstream, self.force, self.tags, self.no_verify):
            self.form.addRow("", w)
        self.validate(lambda: None if self.remote.currentText() else t("err.no_remote"))
        self.finish()


class PullDialog(FormDialog):
    def __init__(self, parent, remotes: list[str], remote: str, branch: str, rebase_default: bool):
        super().__init__(parent, t("pull.title"), t("pull.ok"))
        self.remote = QComboBox()
        self.remote.addItems(remotes)
        if remote:
            self.remote.setCurrentText(remote)
        self.branch = QLineEdit(branch)
        self.rebase = QCheckBox(t("pull.rebase"))
        self.rebase.setChecked(rebase_default)
        self.autostash = QCheckBox(t("pull.autostash"))
        self.autostash.setChecked(True)
        self.form.addRow(t("common.remote"), self.remote)
        self.form.addRow(t("push.remote_branch"), self.branch)
        self.form.addRow("", self.rebase)
        self.form.addRow("", self.autostash)
        self.validate(lambda: None if self.remote.currentText() else t("err.no_remote"))
        self.finish()


class StashDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, t("stash.title"), t("stash.ok"))
        self.message = QLineEdit()
        self.untracked = QCheckBox(t("stash.untracked"))
        self.untracked.setChecked(True)
        self.keep_index = QCheckBox(t("stash.keep_index"))
        self.staged_only = QCheckBox(t("stash.staged_only"))
        self.form.addRow(t("common.message"), self.message)
        for w in (self.untracked, self.keep_index, self.staged_only):
            self.form.addRow("", w)
        self.finish()


class ResetDialog(FormDialog):
    def __init__(self, parent, branch: str, target: str, label: str):
        super().__init__(parent, t("reset.title", branch=branch or "HEAD"), t("reset.ok"))
        self.form.addRow(t("reset.target"), QLabel(f"{target[:10]}  {label}"))
        self.group = QButtonGroup(self)
        self.modes = {}
        for key in ("soft", "mixed", "hard"):
            rb = QRadioButton(t(f"reset.{key}"))
            self.group.addButton(rb)
            self.modes[key] = rb
            self.form.addRow("", rb)
        self.modes["mixed"].setChecked(True)
        self.finish()

    @property
    def mode(self) -> str:
        return next(k for k, rb in self.modes.items() if rb.isChecked())


class RemoteDialog(FormDialog):
    def __init__(self, parent, name: str = "", url: str = ""):
        super().__init__(parent, t("remote.edit") if name else t("remote.add"), t("common.save"))
        self.name = QLineEdit(name or "origin")
        self.name.setReadOnly(bool(name))
        self.url = QLineEdit(url)
        self.url.setPlaceholderText("https://github.com/user/repo.git  /  git@github.com:user/repo.git")
        self.form.addRow(t("common.name"), self.name)
        self.form.addRow("URL", self.url)
        self.validate(lambda: valid_ref_name(self.name.text().strip()))
        self.validate(lambda: None if self.url.text().strip() else t("err.url_empty"))
        self.finish()


class CloneDialog(FormDialog):
    def __init__(self, parent, default_dir: str, url: str = ""):
        super().__init__(parent, t("clone.title"), t("clone.ok"))
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://github.com/owner/repo.git")
        self.parent_dir = QLineEdit(default_dir)
        browse = QPushButton(t("common.browse"))
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.parent_dir, 1)
        row.addWidget(browse)
        self.name = QLineEdit()
        self.branch = QLineEdit()
        self.branch.setPlaceholderText(t("clone.branch_hint"))
        self.depth = QSpinBox()
        self.depth.setRange(0, 100000)
        self.depth.setSpecialValueText(t("clone.full_history"))
        self.recursive = QCheckBox(t("clone.recursive"))
        self.recursive.setChecked(True)
        self.url.textChanged.connect(self._guess)
        self.form.addRow(t("clone.url"), self.url)
        self.form.addRow(t("clone.parent"), row)
        self.form.addRow(t("clone.dirname"), self.name)
        self.form.addRow(t("clone.branch"), self.branch)
        self.form.addRow(t("clone.depth"), self.depth)
        self.form.addRow("", self.recursive)
        self.validate(lambda: None if self.url.text().strip() else t("err.url_empty"))
        self.validate(lambda: None if self.name.text().strip() else t("err.name_empty"))
        self.validate(lambda: t("err.dir_not_empty") if os.path.isdir(self.dest) and os.listdir(self.dest) else None)
        if url:
            self.url.setText(url)
        self.finish()

    @property
    def dest(self) -> str:
        return os.path.join(self.parent_dir.text().strip(), self.name.text().strip())

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, t("common.browse"), self.parent_dir.text())
        if d:
            self.parent_dir.setText(d)

    def _guess(self, url: str):
        base = url.strip().rstrip("/").split("/")[-1].split(":")[-1]
        if base.endswith(".git"):
            base = base[:-4]
        self.name.setText(base)


class WorktreeDialog(FormDialog):
    def __init__(self, parent, repo_path: str, branches: list[str]):
        super().__init__(parent, t("wt.add"), t("common.create"))
        self.branch = editable_combo(branches)
        self.new_branch = QCheckBox(t("wt.new_branch"))
        self.path = QLineEdit()
        browse = QPushButton(t("common.browse"))
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        self.repo_path = repo_path
        self.branch.currentTextChanged.connect(self._guess)
        self.form.addRow(t("common.branch"), self.branch)
        self.form.addRow("", self.new_branch)
        self.form.addRow(t("common.path"), row)
        self._guess(self.branch.currentText())
        self.validate(lambda: valid_ref_name(self.branch.currentText().strip()))
        self.validate(lambda: None if self.path.text().strip() else t("err.path_empty"))
        self.finish()

    def _guess(self, b: str):
        safe = b.replace("/", "-")
        self.path.setText(os.path.join(os.path.dirname(self.repo_path), f"{os.path.basename(self.repo_path)}-{safe}"))

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, t("common.browse"), os.path.dirname(self.repo_path))
        if d:
            self.path.setText(d)


class CleanDialog(FormDialog):
    def __init__(self, parent, files: list[str]):
        super().__init__(parent, t("clean.title"), t("clean.ok"))
        self.buttons.button(QDialogButtonBox.Ok).setObjectName("danger")
        lst = QListWidget()
        lst.addItems(files or [t("clean.nothing")])
        lst.setMinimumHeight(260)
        self.dirs = QCheckBox(t("clean.dirs"))
        self.dirs.setChecked(True)
        self.ignored = QCheckBox(t("clean.ignored"))
        self.form.addRow(lst)
        self.form.addRow("", self.dirs)
        self.form.addRow("", self.ignored)
        warn = QLabel("⚠ " + t("clean.warn"))
        warn.setObjectName("error")
        self.form.addRow(warn)
        self.finish()
