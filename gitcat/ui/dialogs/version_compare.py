"""Compare any two file versions: path@revision vs path@revision, working tree, or files outside the repo."""
from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout)

from ...common.i18n import t
from ..widgets.diff_view import DiffView

if TYPE_CHECKING:
    from ..repo.view import RepoView

WT = ""  # working tree pseudo-revision


class _Side:
    def __init__(self, dlg: "VersionCompareDialog", label: str):
        self.dlg = dlg
        self.caption = QLabel(label)
        self.caption.setObjectName("section")
        self.rev = QComboBox()
        self.rev.setEditable(True)
        self.rev.setMinimumWidth(320)
        self.path = QLineEdit()
        self.browse = QPushButton("…")
        self.browse.setToolTip(t("cmpv.browse"))
        self.browse.setFixedWidth(36)
        self.browse.clicked.connect(self._browse)

    def fill_revs(self, refs: list[str], file_commits: list[tuple[str, str]], current: str):
        self.rev.blockSignals(True)
        self.rev.clear()
        self.rev.addItem("📝 " + t("files.worktree"), WT)
        self.rev.addItem("HEAD", "HEAD")
        for sha, label in file_commits:
            self.rev.addItem(label, sha)
        for r in refs:
            self.rev.addItem(r, r)
        idx = self.rev.findData(current)
        if idx >= 0:
            self.rev.setCurrentIndex(idx)
        elif current:
            self.rev.setEditText(current)
        self.rev.blockSignals(False)

    @property
    def revision(self) -> str:
        i = self.rev.currentIndex()
        if i >= 0 and self.rev.itemText(i) == self.rev.currentText():
            return self.rev.itemData(i) or WT
        return self.rev.currentText().strip()

    def _browse(self):
        start = self.dlg.rw.repo.path
        p, _ = QFileDialog.getOpenFileName(self.dlg, t("cmpv.browse"), start)
        if not p:
            return
        root = os.path.normcase(os.path.abspath(self.dlg.rw.repo.path))
        ap = os.path.abspath(p)
        if os.path.normcase(ap).startswith(root + os.sep):
            self.path.setText(os.path.relpath(ap, self.dlg.rw.repo.path).replace(os.sep, "/"))
        else:
            self.path.setText(ap)  # external file → compared from disk
            self.rev.setCurrentIndex(0)
        self.dlg.refresh_revs()


class VersionCompareDialog(QDialog):
    def __init__(self, rw: "RepoView", path_a: str, rev_a: str = "HEAD", path_b: Optional[str] = None,
                 rev_b: str = WT):
        super().__init__(rw)
        self.rw = rw
        self._initial: Optional[tuple[str, str]] = None
        self.setWindowTitle("⇄ " + t("cmpv.title"))
        self.resize(1400, 880)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        grid = QGridLayout()
        self.a, self.b = _Side(self, t("cmpv.left")), _Side(self, t("cmpv.right"))
        for row, side in enumerate((self.a, self.b)):
            grid.addWidget(side.caption, row, 0)
            grid.addWidget(side.rev, row, 1)
            grid.addWidget(side.path, row, 2)
            grid.addWidget(side.browse, row, 3)
        grid.setColumnStretch(2, 1)
        lay.addLayout(grid)
        btns = QHBoxLayout()
        swap = QPushButton("⇅ " + t("cmpv.swap"))
        go = QPushButton("⇄ " + t("cmpv.compare"))
        go.setObjectName("primary")
        self.summary = QLabel("")
        self.summary.setObjectName("muted")
        btns.addWidget(self.summary, 1)
        btns.addWidget(swap)
        btns.addWidget(go)
        lay.addLayout(btns)
        self.diff = DiffView()
        self.diff.sbs_box.setChecked(True)
        lay.addWidget(self.diff, 1)
        self.refs = rw.repo.all_refs_for_picker()
        self.a.path.setText(path_a)
        self.b.path.setText(path_b if path_b is not None else path_a)
        self._initial = (rev_a, rev_b)
        self.refresh_revs()
        swap.clicked.connect(self._swap)
        go.clicked.connect(self.compare)
        for side in (self.a, self.b):
            side.rev.activated.connect(lambda _: self.compare())
            side.path.returnPressed.connect(lambda: (self.refresh_revs(), self.compare()))
        self.diff.optionsChanged.connect(self.compare)
        self.compare()

    def _file_commits(self, path: str) -> list[tuple[str, str]]:
        if not path or os.path.isabs(path):
            return []
        try:
            commits = self.rw.repo.file_revisions(path, 200)
        except Exception:  # noqa: BLE001
            return []
        return [(c.sha, f"{c.short}  {datetime.fromtimestamp(c.timestamp):%Y-%m-%d}  {c.subject[:60]}")
                for c in commits]

    def refresh_revs(self):
        init = self._initial or (self.a.revision, self.b.revision)
        self._initial = None
        for side, cur in ((self.a, init[0]), (self.b, init[1])):
            side.fill_revs(self.refs, self._file_commits(side.path.text().strip()), cur)

    def _swap(self):
        ra, rb = self.a.revision, self.b.revision
        pa, pb = self.a.path.text(), self.b.path.text()
        self.a.path.setText(pb)
        self.b.path.setText(pa)
        self._initial = (rb, ra)
        self.refresh_revs()
        self.compare()

    def compare(self):
        repo = self.rw.repo
        ra, rb = self.a.revision, self.b.revision
        pa, pb = self.a.path.text().strip(), self.b.path.text().strip()
        if not pa or not pb:
            return
        ctx, ws = self.diff.context, self.diff.ignore_ws
        title = f"{pa} @ {ra or t('files.worktree')}   ⇄   {pb} @ {rb or t('files.worktree')}"

        def work():
            if os.path.isabs(pa) or os.path.isabs(pb):
                fa = pa if os.path.isabs(pa) else os.path.join(repo.path, pa)
                fb = pb if os.path.isabs(pb) else os.path.join(repo.path, pb)
                return repo.diff_paths(fa, fb, ctx, ws)
            return repo.diff_versions(ra, pa, rb, pb, ctx, ws)

        def done(data: bytes):
            if not data.strip():
                self.diff.set_diff(b"", "readonly", title, t("cmpv.identical"))
                self.summary.setText(t("cmpv.identical"))
                return
            self.diff.set_diff(data, "readonly", title)
            self.summary.setText(self.diff.stat.text())
        self.rw.bg(work, done, lambda e: self.diff.set_diff(b"", "readonly", title, str(e)), "")
