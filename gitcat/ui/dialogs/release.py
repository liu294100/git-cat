"""One-click release wizard dialog."""
from __future__ import annotations


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QPushButton)

from ...common.i18n import t
from ...core.validation import valid_ref_name
from ...services.release import VersionFile, bump
from .base import FormDialog


class ReleaseDialog(FormDialog):
    """One-click release: bump version files, update changelog, commit, annotated tag, push."""

    def __init__(self, parent, latest_tag: str, files: list[VersionFile], notes: str, remotes: list[str],
                 branch: str, has_workflow: bool):
        super().__init__(parent, "🚀 " + t("release.title"), t("release.ok"))
        self.setMinimumWidth(720)
        base = latest_tag or (files[0].version if files else "")
        info = QLabel(t("release.latest", tag=latest_tag or t("release.none")) + "   ·   " +
                      t("release.branch", branch=branch or "HEAD"))
        info.setObjectName("muted")
        self.form.addRow(info)
        self.version = QLineEdit(bump(base.lstrip("v"), "patch"))
        bumps = QHBoxLayout()
        bumps.addWidget(self.version, 1)
        for part in ("patch", "minor", "major"):
            b = QPushButton(f"{part} → {bump(base.lstrip('v'), part)}")
            b.clicked.connect(lambda _=False, p=part: self.version.setText(bump(base.lstrip("v"), p)))
            bumps.addWidget(b)
        self.form.addRow(t("release.version"), bumps)
        self.prefix = QCheckBox(t("release.prefix_v"))
        self.prefix.setChecked(not latest_tag or latest_tag.startswith("v"))
        self.form.addRow("", self.prefix)
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(110)
        for vf in files:
            it = QListWidgetItem(f"{vf.path}   ({vf.version})")
            it.setData(Qt.UserRole, vf)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            self.file_list.addItem(it)
        if not files:
            it = QListWidgetItem(t("release.no_files"))
            it.setFlags(Qt.NoItemFlags)
            self.file_list.addItem(it)
        self.form.addRow(t("release.files"), self.file_list)
        self.notes = QPlainTextEdit(notes)
        self.notes.setMinimumHeight(150)
        self.form.addRow(t("release.notes"), self.notes)
        self.changelog = QCheckBox(t("release.changelog"))
        self.changelog.setChecked(True)
        self.remote = QComboBox()
        self.remote.addItems(remotes)
        self.push = QCheckBox(t("release.push"))
        self.push.setChecked(bool(remotes))
        self.push.setEnabled(bool(remotes))
        prow = QHBoxLayout()
        prow.addWidget(self.push)
        prow.addWidget(self.remote, 1)
        self.form.addRow("", self.changelog)
        self.form.addRow("", prow)
        hint = QLabel(("✅ " + t("release.has_workflow")) if has_workflow else ("💡 " + t("release.no_workflow")))
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        self.form.addRow(hint)
        self.validate(lambda: None if self.version.text().strip() else t("err.name_empty"))
        self.validate(lambda: valid_ref_name(self.tag))
        self.finish()

    @property
    def tag(self) -> str:
        v = self.version.text().strip().lstrip("v")
        return ("v" if self.prefix.isChecked() else "") + v

    def selected_files(self) -> list[VersionFile]:
        res = []
        for i in range(self.file_list.count()):
            it = self.file_list.item(i)
            vf = it.data(Qt.UserRole)
            if vf and it.checkState() == Qt.Checked:
                res.append(vf)
        return res
