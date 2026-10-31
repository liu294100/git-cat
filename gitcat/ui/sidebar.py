"""Repository sidebar: branches / remotes / tags / stashes / submodules / worktrees."""
from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QMenu, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..common.i18n import t
from ..common.text import remote_web_url
from ..core.models import Ref, Submodule, Worktree
from ..core.versioning import semver_key
from . import theme

if TYPE_CHECKING:
    from .repo.view import RepoView

ROLE_KIND = Qt.UserRole
ROLE_DATA = Qt.UserRole + 1
TRACK_RE = re.compile(r"(ahead|behind) (\d+)")


class Sidebar(QWidget):
    def __init__(self, rw: "RepoView"):
        super().__init__()
        self.rw = rw
        self._collapsed: set[str] = set()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 0, 6)
        lay.setSpacing(6)
        self.head = QLabel("")
        self.head.setObjectName("card")
        self.head.setTextFormat(Qt.RichText)
        self.head.setStyleSheet("padding: 10px 12px;")
        self.head.setWordWrap(True)
        lay.addWidget(self.head)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("🔎 " + t("side.filter"))
        self.filter.setClearButtonEnabled(True)
        lay.addWidget(self.filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.setAnimated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        lay.addWidget(self.tree, 1)
        self.tree.itemDoubleClicked.connect(self._activate)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.itemCollapsed.connect(lambda it: self._collapsed.add(self._key(it)))
        self.tree.itemExpanded.connect(lambda it: self._collapsed.discard(self._key(it)))
        self.filter.textChanged.connect(self._apply_filter)

    @staticmethod
    def _key(it: QTreeWidgetItem) -> str:
        parts = []
        while it is not None:
            parts.append(it.text(0))
            it = it.parent()
        return "/".join(reversed(parts))

    def _section(self, title: str, kind: str, count: int) -> QTreeWidgetItem:
        it = QTreeWidgetItem([f"{title}   {count}"])
        it.setData(0, ROLE_KIND, kind)
        f = QFont()
        f.setBold(True)
        f.setPointSizeF(9)
        it.setFont(0, f)
        it.setForeground(0, theme.color("muted"))
        it.setFlags(it.flags() & ~Qt.ItemIsSelectable)
        self.tree.addTopLevelItem(it)
        return it

    def _folder(self, parent: QTreeWidgetItem, path: list[str], cache: dict) -> QTreeWidgetItem:
        node = parent
        acc = ""
        for p in path:
            acc += "/" + p
            key = (id(parent), acc)
            if key not in cache:
                ch = QTreeWidgetItem(["📁 " + p])
                ch.setData(0, ROLE_KIND, "folder")
                ch.setForeground(0, theme.color("muted"))
                node.addChild(ch)
                cache[key] = ch
            node = cache[key]
        return node

    def _leaf(self, parent, text: str, kind: str, data, tip: str = "", color: str = "", bold=False):
        it = QTreeWidgetItem([text])
        it.setData(0, ROLE_KIND, kind)
        it.setData(0, ROLE_DATA, data)
        if tip:
            it.setToolTip(0, tip)
        if color:
            it.setForeground(0, QColor(color))
        if bold:
            f = QFont()
            f.setBold(True)
            it.setFont(0, f)
        parent.addChild(it)
        return it

    def fill(self, refs: list[Ref], remotes: dict[str, str], stashes: list[tuple[str, str, str]],
             subs: list[Submodule], worktrees: list[Worktree], branch: str, ahead: int, behind: int, state_label: str):
        C = theme.C
        sync = []
        if ahead:
            sync.append(f"<span style='color:{C['ok']}'>↑{ahead}</span>")
        if behind:
            sync.append(f"<span style='color:{C['warn']}'>↓{behind}</span>")
        self.head.setText(
            f"<div style='font-size:11px;color:{C['muted']}'>{t('side.current')}</div>"
            f"<div style='font-size:15px;font-weight:800;color:{C['text']}'>⎇ {branch or t('side.detached')} "
            f"{' '.join(sync)}</div>" + (f"<div style='color:{C['warn']}'>⚠ {state_label}</div>" if state_label else ""))
        scroll = self.tree.verticalScrollBar().value()
        self.tree.clear()
        cache: dict = {}
        locals_ = [r for r in refs if r.kind == "local"]
        sec = self._section("⎇  " + t("side.branches"), "sec_local", len(locals_))
        for r in sorted(locals_, key=lambda r: r.name.lower()):
            parts = r.name.split("/")
            parent = self._folder(sec, parts[:-1], cache)
            badges = []
            for k, n in TRACK_RE.findall(r.track):
                badges.append(("↑" if k == "ahead" else "↓") + n)
            if r.track == "[gone]":
                badges.append("✖")
            label = ("● " if r.is_head else "") + parts[-1] + ("   " + " ".join(badges) if badges else "")
            tip = r.name + (f"\n→ {r.upstream} {r.track}" if r.upstream else "") + f"\n{r.sha[:10]} {r.subject}"
            self._leaf(parent, label, "local", r, tip, C["ok"] if r.is_head else "", r.is_head)
        remote_refs = [r for r in refs if r.kind == "remote"]
        sec = self._section("☁  " + t("side.remotes"), "sec_remote", len(remotes))
        for name, url in remotes.items():
            node = self._leaf(sec, f"🌐 {name}", "remote", name, url)
            for r in sorted([r for r in remote_refs if r.remote == name], key=lambda r: r.name.lower()):
                parts = r.branch_on_remote.split("/")
                parent = self._folder(node, parts[:-1], cache)
                self._leaf(parent, parts[-1], "rbranch", r, f"{r.name}\n{r.sha[:10]} {r.subject}")
        tags = sorted([r for r in refs if r.kind == "tag"], key=lambda r: semver_key(r.name), reverse=True)
        sec = self._section("◆  " + t("side.tags"), "sec_tag", len(tags))
        for r in tags:
            self._leaf(sec, r.name, "tag", r, f"{r.name}\n{r.sha[:10]} {r.subject}", C["warn"])
        sec = self._section("📦  " + t("side.stashes"), "sec_stash", len(stashes))
        for ref, msg, when in stashes:
            self._leaf(sec, msg, "stash", ref, f"{ref} · {when}")
        if subs:
            sec = self._section("🧩  " + t("side.submodules"), "sec_sub", len(subs))
            for s in subs:
                mark = {"-": "○", "+": "●", "U": "⚠"}.get(s.state, "✔")
                self._leaf(sec, f"{mark} {s.path}", "sub", s, f"{s.sha[:10]} {s.describe}")
        sec = self._section("🌳  " + t("side.worktrees"), "sec_wt", len(worktrees))
        for w in worktrees:
            cur = os.path.normcase(w.path) == os.path.normcase(self.rw.repo.path)
            self._leaf(sec, f"{'● ' if cur else ''}{os.path.basename(w.path)}  [{w.branch or w.head[:8]}]", "wt", w,
                       w.path, C["accent2"] if cur else "")
        self._restore_expansion(self.tree.invisibleRootItem())
        self._apply_filter(self.filter.text())
        self.tree.verticalScrollBar().setValue(scroll)

    def _restore_expansion(self, node: QTreeWidgetItem):
        for i in range(node.childCount()):
            ch = node.child(i)
            if ch.childCount():
                ch.setExpanded(self._key(ch) not in self._collapsed)
                self._restore_expansion(ch)

    def _apply_filter(self, q: str):
        q = q.lower().strip()

        def visit(it: QTreeWidgetItem) -> bool:
            """Return True when the item or one of its descendants matches."""
            any_child = False
            for i in range(it.childCount()):
                any_child = visit(it.child(i)) or any_child
            kind = it.data(0, ROLE_KIND) or ""
            if kind.startswith("sec_"):
                it.setHidden(False)
                if q and any_child:
                    it.setExpanded(True)
                return any_child
            match = not q or q in it.text(0).lower() or any_child
            it.setHidden(not match)
            if q and any_child:
                it.setExpanded(True)
            return match

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            visit(root.child(i))

    # ---------------------------------------------------------------- actions
    def _activate(self, it: QTreeWidgetItem, _col: int = 0):
        kind, data = it.data(0, ROLE_KIND), it.data(0, ROLE_DATA)
        rw = self.rw
        if kind == "local" and not data.is_head:
            rw.checkout_ref(data.name)
        elif kind == "rbranch":
            rw.checkout_remote(data)
        elif kind in ("tag", "local"):
            rw.show_commit(data.sha)
        elif kind == "stash":
            rw.show_page("stash")
        elif kind == "sub":
            rw.main.open_repo(os.path.join(rw.repo.path, data.path))
        elif kind == "wt":
            rw.main.open_repo(data.path)

    def _menu(self, pos):
        it = self.tree.itemAt(pos)
        if not it:
            return
        kind, data = it.data(0, ROLE_KIND), it.data(0, ROLE_DATA)
        rw = self.rw
        m = QMenu(self)
        cur = rw.repo.current_branch() or "HEAD"
        clip = QApplication.clipboard()
        if kind == "sec_local":
            m.addAction("＋ " + t("branch.new"), lambda: rw.new_branch())
        elif kind == "sec_remote":
            m.addAction("＋ " + t("remote.add"), rw.add_remote)
            m.addAction("⟳ " + t("tb.fetch_all"), lambda: rw.fetch())
        elif kind == "sec_tag":
            m.addAction("＋ " + t("tag.new"), lambda: rw.new_tag())
            m.addAction("🚀 " + t("release.title"), rw.release)
            m.addAction("⇪ " + t("tag.push_all"), rw.push_all_tags)
        elif kind == "sec_stash":
            m.addAction("＋ " + t("stash.title"), rw.stash)
        elif kind == "sec_wt":
            m.addAction("＋ " + t("wt.add"), rw.add_worktree)
            m.addAction(t("wt.prune"), lambda: rw.op(rw.repo.prune_worktrees, t("wt.prune")))
        elif kind == "sec_sub":
            m.addAction(t("sub.update"), lambda: rw.op(rw.repo.submodule_update, t("sub.update")))
            m.addAction(t("sub.update_remote"),
                        lambda: rw.op(lambda: rw.repo.submodule_update(remote=True), t("sub.update_remote")))
        elif kind == "local":
            r: Ref = data
            if not r.is_head:
                m.addAction("⎇  " + t("branch.checkout"), lambda: rw.checkout_ref(r.name))
                m.addAction(t("branch.merge_into", src=r.name, dst=cur), lambda: rw.merge(preset=r.name))
                m.addAction(t("branch.rebase_onto", cur=cur, onto=r.name), lambda: rw.rebase_onto(r.name, r.name))
                m.addAction(t("branch.compare", a=cur, b=r.name), lambda: rw.compare("HEAD", r.name))
            else:
                m.addAction("⇪ " + t("tb.push"), rw.push)
                m.addAction("⇩ " + t("tb.pull"), rw.pull)
            m.addSeparator()
            m.addAction("⇪ " + t("branch.push_this"), lambda: rw.push(local=r.name))
            if r.upstream:
                m.addAction("⤴ " + t("ci.new_pr"), lambda: rw.open_pr(r.upstream.split("/", 1)[-1],
                                                                       r.upstream.split("/", 1)[0]))
                m.addAction("🌐 " + t("ci.compare_web"), lambda: rw.open_compare_web("", r.upstream.split("/", 1)[-1]))
            m.addAction("＋ " + t("branch.new_from", name=r.name), lambda: rw.new_branch(r.name, r.name))
            m.addAction("◆  " + t("tag.new_here"), lambda: rw.new_tag(r.name, r.name))
            m.addAction(t("branch.rename"), lambda: rw.rename_branch(r.name))
            m.addAction(t("branch.set_upstream"), lambda: rw.set_upstream(r.name))
            m.addAction(t("branch.show"), lambda: rw.show_commit(r.sha))
            m.addSeparator()
            m.addAction(t("common.copy_name"), lambda: clip.setText(r.name))
            if not r.is_head:
                m.addSeparator()
                m.addAction("🗑 " + t("branch.delete"), lambda: rw.delete_branch(r))
        elif kind == "rbranch":
            r = data
            m.addAction("⎇  " + t("branch.checkout_tracking"), lambda: rw.checkout_remote(r))
            m.addAction(t("branch.merge_into", src=r.name, dst=cur), lambda: rw.merge(preset=r.name))
            m.addAction(t("branch.rebase_onto", cur=cur, onto=r.name), lambda: rw.rebase_onto(r.name, r.name))
            m.addAction(t("branch.compare", a=cur, b=r.name), lambda: rw.compare("HEAD", r.name))
            m.addAction(t("branch.show"), lambda: rw.show_commit(r.sha))
            m.addAction("＋ " + t("branch.new_from", name=r.name), lambda: rw.new_branch(r.name, r.name))
            m.addSeparator()
            m.addAction("⤴ " + t("ci.new_pr"), lambda: rw.open_pr(r.branch_on_remote, r.remote))
            m.addAction("🌐 " + t("ci.branch_web"), lambda: rw.open_branch_web(r.branch_on_remote, r.remote))
            m.addSeparator()
            m.addAction(t("common.copy_name"), lambda: clip.setText(r.name))
            m.addAction("🗑 " + t("branch.delete_remote"), lambda: rw.delete_remote_branch(r))
        elif kind == "remote":
            name = data
            url = rw.repo.remotes().get(name, "")
            info = rw.remote_info(name)
            m.addAction("⟳ " + t("remote.fetch", name=name), lambda: rw.fetch(name))
            m.addAction("🌐 " + t("remote.open_web"), lambda: rw.open_url(info.web if info else remote_web_url(url)))
            if info:
                m.addAction("⚙ " + t("ci.open_ci"), lambda: rw.open_url(info.ci_url))
            m.addAction("👤 " + t("acc.title") + "…", lambda: rw.main.accounts_dialog(info))
            m.addAction(t("remote.edit"), lambda: rw.edit_remote(name, url))
            m.addAction(t("common.copy") + " URL", lambda: clip.setText(url))
            m.addSeparator()
            m.addAction("🗑 " + t("remote.remove"), lambda: rw.remove_remote(name))
        elif kind == "tag":
            r = data
            m.addAction(t("branch.show"), lambda: rw.show_commit(r.sha))
            m.addAction("⎇  " + t("tag.checkout"), lambda: rw.checkout_ref(r.name, detached=True))
            m.addAction("＋ " + t("branch.new_from", name=r.name), lambda: rw.new_branch(r.name, r.name))
            m.addAction("⇪ " + t("tag.push"), lambda: rw.push_tag(r.name))
            m.addAction(t("hist.archive"), lambda: rw.archive(r.name))
            m.addAction(t("common.copy_name"), lambda: clip.setText(r.name))
            m.addSeparator()
            m.addAction("🗑 " + t("tag.delete"), lambda: rw.delete_tag(r.name, remote=False))
            m.addAction("🗑 " + t("tag.delete_remote"), lambda: rw.delete_tag(r.name, remote=True))
        elif kind == "stash":
            ref = data
            m.addAction(t("stash.apply"), lambda: rw.stash_apply(ref, False))
            m.addAction(t("stash.pop"), lambda: rw.stash_apply(ref, True))
            m.addAction(t("stash.to_branch"), lambda: rw.stash_branch(ref))
            m.addSeparator()
            m.addAction("🗑 " + t("stash.drop"), lambda: rw.stash_drop(ref))
        elif kind == "sub":
            s: Submodule = data
            m.addAction(t("sub.open"), lambda: rw.main.open_repo(os.path.join(rw.repo.path, s.path)))
            m.addAction(t("sub.update"), lambda: rw.op(rw.repo.submodule_update, t("sub.update")))
        elif kind == "wt":
            w: Worktree = data
            m.addAction(t("wt.open"), lambda: rw.main.open_repo(w.path))
            if os.path.normcase(w.path) != os.path.normcase(rw.repo.path):
                m.addAction("🗑 " + t("wt.remove"), lambda: rw.remove_worktree(w))
        if not m.isEmpty():
            m.exec(self.tree.viewport().mapToGlobal(pos))
