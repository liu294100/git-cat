"""Application settings dialog."""
from __future__ import annotations

import os

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox)

from ...common.i18n import LANGUAGES, t
from .. import theme
from .base import FormDialog


class SettingsDialog(FormDialog):
    def __init__(self, parent, cfg: dict, user_name: str, user_email: str):
        super().__init__(parent, t("settings.title"), t("common.save"))
        self.setMinimumWidth(640)
        g1 = QGroupBox(t("settings.appearance"))
        f1 = QFormLayout(g1)
        self.lang = QComboBox()
        for code, native in LANGUAGES.items():
            self.lang.addItem(native, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(cfg.get("language", "en"))))
        self.theme = QComboBox()
        for key in theme.THEMES:
            self.theme.addItem(t(f"theme.{key}"), key)
        self.theme.setCurrentIndex(max(0, self.theme.findData(cfg.get("theme", "neon"))))
        f1.addRow(t("settings.language"), self.lang)
        f1.addRow(t("settings.theme"), self.theme)
        self.outer.insertWidget(1, g1)

        g2 = QGroupBox(t("settings.identity"))
        f2 = QFormLayout(g2)
        self.user_name = QLineEdit(user_name)
        self.user_email = QLineEdit(user_email)
        f2.addRow(t("settings.user_name"), self.user_name)
        f2.addRow(t("settings.user_email"), self.user_email)
        self.outer.insertWidget(2, g2)

        g3 = QGroupBox(t("settings.behavior"))
        f3 = QFormLayout(g3)
        self.clone_dir = QLineEdit(cfg.get("clone_dir", os.path.expanduser("~")))
        self.editor = QLineEdit(cfg.get("editor", ""))
        self.editor.setPlaceholderText("code / kiro / notepad++ ...")
        self.auto_fetch = QSpinBox()
        self.auto_fetch.setRange(0, 240)
        self.auto_fetch.setSuffix(" min")
        self.auto_fetch.setSpecialValueText(t("settings.off"))
        self.auto_fetch.setValue(int(cfg.get("auto_fetch_min", 10)))
        self.check_updates = QCheckBox(t("settings.check_updates"))
        self.check_updates.setChecked(cfg.get("check_updates", True))
        self.pull_rebase = QCheckBox(t("settings.pull_rebase"))
        self.pull_rebase.setChecked(cfg.get("pull_rebase", False))
        f3.addRow(t("settings.clone_dir"), self.clone_dir)
        f3.addRow(t("settings.editor"), self.editor)
        f3.addRow(t("settings.auto_fetch"), self.auto_fetch)
        f3.addRow("", self.pull_rebase)
        f3.addRow("", self.check_updates)
        self.outer.insertWidget(3, g3)

        g4 = QGroupBox(t("acc.title"))
        f4 = QHBoxLayout(g4)
        n = len(cfg.get("accounts", []))
        lbl = QLabel(t("settings.accounts_hint", n=n))
        lbl.setWordWrap(True)
        f4.addWidget(lbl, 1)
        self.open_accounts = QPushButton("👤 " + t("acc.title") + "…")
        f4.addWidget(self.open_accounts)
        self.outer.insertWidget(4, g4)
        self.finish()

    def apply_to(self, cfg: dict):
        cfg["language"] = self.lang.currentData()
        cfg["theme"] = self.theme.currentData()
        cfg["clone_dir"] = self.clone_dir.text().strip()
        cfg["editor"] = self.editor.text().strip()
        cfg["auto_fetch_min"] = self.auto_fetch.value()
        cfg["check_updates"] = self.check_updates.isChecked()
        cfg["pull_rebase"] = self.pull_rebase.isChecked()
        cfg.pop("github_token", None)
