"""Command Center: a form for every git command in the catalogue, with live preview and output."""
from __future__ import annotations

import os
import shlex
import webbrowser
from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ...common.i18n import t
from ...core.runner import decode, run_git, run_git_stream
from ...services.command_catalog import CATALOG, GROUPS, Command, build_argv, preview
from .. import theme

if TYPE_CHECKING:
    from ..main_window import MainWindow
    from ..repo.view import RepoView


class CommandCenter(QDialog):
    def __init__(self, main: "MainWindow", rv: Optional["RepoView"]):
        super().__init__(main)
        self.main, self.rv = main, rv
        self.cmd: Optional[Command] = None
        self.inputs: list[Callable[[], object]] = []
        self.setWindowTitle("⌨ " + t("cc.title"))
        self.resize(1320, 860)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        split = QSplitter(Qt.Horizontal)
        lay.addWidget(split)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 " + t("cc.search"))
        self.search.setClearButtonEnabled(True)
        ll.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        ll.addWidget(self.tree, 1)
        n = QLabel(t("cc.count", n=len(CATALOG)))
        n.setObjectName("muted")
        ll.addWidget(n)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        head = QHBoxLayout()
        self.title = QLabel("")
        self.title.setStyleSheet("font-size: 18px; font-weight: 800;")
        head.addWidget(self.title, 1)
        self.doc = QPushButton("📖 " + t("cc.docs"))
        head.addWidget(self.doc)
        rl.addLayout(head)
        self.desc = QLabel("")
        self.desc.setObjectName("muted")
        self.desc.setWordWrap(True)
        rl.addWidget(self.desc)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(220)
        rl.addWidget(self.scroll, 2)
        self.preview = QLineEdit()
        self.preview.setFont(QFont("Consolas", 10))
        self.preview.setReadOnly(True)
        rl.addWidget(self.preview)
        row = QHBoxLayout()
        self.where = QLabel("")
        self.where.setObjectName("muted")
        row.addWidget(self.where, 1)
        copy = QPushButton(t("common.copy"))
        self.run_btn = QPushButton("▶ " + t("cc.run"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumWidth(140)
        row.addWidget(copy)
        row.addWidget(self.run_btn)
        rl.addLayout(row)
        raw = QHBoxLayout()
        self.raw = QComboBox()
        self.raw.setEditable(True)
        self.raw.lineEdit().setPlaceholderText(t("cc.raw_hint"))
        self.raw.addItems(main.cfg.get("cmd_history", []))
        self.raw.setCurrentText("")
        raw_run = QPushButton("▶")
        raw_run.setToolTip(t("cc.run"))
        raw.addWidget(QLabel("git"))
        raw.addWidget(self.raw, 1)
        raw.addWidget(raw_run)
        rl.addLayout(raw)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("Consolas", 10))
        self.out.setMaximumBlockCount(20000)
        rl.addWidget(self.out, 3)
        split.addWidget(right)
        split.setSizes([300, 1000])

        self._fill_tree("")
        self.search.textChanged.connect(self._fill_tree)
        self.tree.currentItemChanged.connect(lambda it, _: it and it.data(0, Qt.UserRole) and
                                             self._select(it.data(0, Qt.UserRole)))
        self.doc.clicked.connect(lambda: self.cmd and webbrowser.open(self.cmd.doc_url))
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.preview.text()))
        self.run_btn.clicked.connect(self._run_form)
        raw_run.clicked.connect(self._run_raw)
        self.raw.lineEdit().returnPressed.connect(self._run_raw)
        self.where.setText("📁 " + (rv.repo.path if rv else os.path.expanduser("~")))
        first = self.tree.topLevelItem(0)
        if first and first.childCount():
            self.tree.setCurrentItem(first.child(0))

    # ---------------------------------------------------------------- catalogue
    def _fill_tree(self, q: str):
        q = q.lower().strip()
        self.tree.clear()
        for g in GROUPS:
            cmds = [c for c in CATALOG if c.group == g and (not q or q in c.id or q in c.desc.lower()
                                                           or q in " ".join(c.args))]
            if not cmds:
                continue
            top = QTreeWidgetItem([f"{t('cc.group.' + g)}   {len(cmds)}"])
            top.setForeground(0, theme.color("muted"))
            top.setFlags(top.flags() & ~Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(top)
            for c in cmds:
                it = QTreeWidgetItem([("⚠ " if c.danger else "") + "git " + " ".join(c.args[:2]).replace(" --progress", "")
                                      + ("" if c.id.split("-")[0] == c.args[0] else f"  ·  {c.id}")])
                it.setData(0, Qt.UserRole, c.id)
                it.setToolTip(0, c.desc)
                if c.danger:
                    it.setForeground(0, theme.color("warn"))
                top.addChild(it)
            top.setExpanded(True)

    def _select(self, cmd_id: str):
        cmd = next(c for c in CATALOG if c.id == cmd_id)
        self.cmd = cmd
        self.title.setText(("⚠ " if cmd.danger else "") + "git " + " ".join(cmd.args))
        self.desc.setText(cmd.desc + ("" if self.rv or not cmd.needs_repo else "   ·   " + t("cc.needs_repo")))
        form_w = QWidget()
        form = QFormLayout(form_w)
        form.setLabelAlignment(Qt.AlignRight)
        self.inputs = []
        refs = self.rv.repo.all_refs_for_picker() if self.rv else []
        remotes = list(self.rv.repo.remotes()) if self.rv else []
        for fd in cmd.fields:
            label = fd.title
            if fd.kind == "flag":
                w = QCheckBox(fd.label or fd.flag)
                if fd.label and fd.label != fd.flag:
                    w.setToolTip(fd.flag)
                w.setChecked(bool(fd.default))
                w.toggled.connect(lambda _: self._update_preview())
                form.addRow("", w)
                self.inputs.append(w.isChecked)
                continue
            if fd.kind in ("choice", "ref", "remote"):
                w = QComboBox()
                w.setEditable(fd.kind != "choice")
                items = list(fd.choices) if fd.kind == "choice" else (remotes if fd.kind == "remote" else refs)
                if fd.kind != "choice":
                    w.addItem("")
                w.addItems(items)
                if fd.default is not None:
                    w.setCurrentText(str(fd.default))
                elif fd.kind == "remote" and remotes:
                    w.setCurrentText(remotes[0])
                w.currentTextChanged.connect(lambda _: self._update_preview())
                if w.isEditable() and fd.hint:
                    w.lineEdit().setPlaceholderText(fd.hint)
                self.inputs.append(w.currentText)
                widget = w
            else:
                w = QLineEdit("" if fd.default is None else str(fd.default))
                w.setPlaceholderText(fd.hint or ("…" if fd.kind != "paths" else t("cc.paths_hint")))
                w.textChanged.connect(lambda _: self._update_preview())
                self.inputs.append(w.text)
                widget = w
                if fd.kind == "path":
                    box = QWidget()
                    hl = QHBoxLayout(box)
                    hl.setContentsMargins(0, 0, 0, 0)
                    hl.addWidget(w, 1)
                    b = QPushButton("…")
                    b.setFixedWidth(36)
                    b.clicked.connect(lambda _=False, e=w: self._browse(e))
                    hl.addWidget(b)
                    widget = box
            form.addRow(label + (" *" if fd.required else ""), widget)
        if not cmd.fields:
            form.addRow(QLabel(t("cc.no_options")))
        self.scroll.setWidget(form_w)
        self.run_btn.setEnabled(bool(self.rv) or not cmd.needs_repo)
        self._update_preview()

    def _browse(self, edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, t("common.browse"), edit.text() or os.path.expanduser("~"))
        if d:
            edit.setText(d)

    def _values(self) -> dict[str, object]:
        return {str(i): get() for i, get in enumerate(self.inputs)}

    def _update_preview(self):
        if not self.cmd:
            return
        try:
            self.preview.setText(preview(build_argv(self.cmd, self._values())))
            self.preview.setStyleSheet("")
        except ValueError as e:
            self.preview.setText(t("cc.required", f=str(e)))
            self.preview.setStyleSheet(f"color: {theme.C['danger']};")

    # ---------------------------------------------------------------- running
    def _run_form(self):
        if not self.cmd:
            return
        try:
            argv = build_argv(self.cmd, self._values())
        except ValueError as e:
            QMessageBox.warning(self, t("cc.title"), t("cc.required", f=str(e)))
            return
        if self.cmd.danger and QMessageBox.question(self, t("cc.title"), t("cc.danger", cmd=preview(argv))) \
                != QMessageBox.Yes:
            return
        self._execute(argv, self.cmd.network, self.cmd.needs_repo)

    def _run_raw(self):
        line = self.raw.currentText().strip()
        if line.lower().startswith("git "):
            line = line[4:]
        if not line:
            return
        try:
            argv = shlex.split(line, posix=os.name != "nt")
        except ValueError as e:
            QMessageBox.warning(self, t("cc.title"), str(e))
            return
        argv = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a for a in argv]
        hist = [h for h in self.main.cfg.get("cmd_history", []) if h != line]
        self.main.cfg["cmd_history"] = [line] + hist[:99]
        net = argv[:1] and argv[0] in ("fetch", "pull", "push", "clone", "ls-remote")
        self._execute(argv, bool(net), False)

    def _execute(self, argv: list[str], network: bool, needs_repo: bool):
        cwd = self.rv.repo.path if self.rv else os.path.expanduser("~")
        C = theme.C
        self.out.appendHtml(f"<b style='color:{C['accent2']}'>$ {preview(argv).replace('<', '&lt;')}</b>")
        self.run_btn.setEnabled(False)

        def work(progress):
            if network:
                return run_git_stream(argv, cwd, progress)
            code, out, err = run_git(argv, cwd)
            return code, decode(out), decode(err)

        def done(res):
            code, out, err = res
            self.run_btn.setEnabled(True)
            body = (out + ("\n" if out and err else "") + err).rstrip()
            if body:
                self.out.appendPlainText(body[-200000:])
            color = C["ok"] if code == 0 else C["danger"]
            self.out.appendHtml(f"<span style='color:{color}'>exit {code}</span><br>")
            self.main.bridge.log.emit("git " + " ".join(argv), code, out, err)
            if self.rv:
                self.rv.refresh(force_log=True)

        def fail(e):
            self.run_btn.setEnabled(True)
            self.out.appendPlainText(str(e))
        self.main.run_job(work, done, fail, "git " + (argv[0] if argv else ""), progress=True)
