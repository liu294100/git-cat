"""Plain data objects describing git state (no Qt, no I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field


CONFLICT_CODES = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}


@dataclass
class Commit:
    sha: str
    parents: list[str]
    author: str
    email: str
    timestamp: int
    subject: str
    refs: list[str] = field(default_factory=list)

    @property
    def short(self) -> str:
        return self.sha[:8]


@dataclass
class FileChange:
    path: str
    x: str = " "
    y: str = " "
    orig_path: str = ""

    @property
    def conflicted(self) -> bool:
        return (self.x + self.y) in CONFLICT_CODES

    @property
    def untracked(self) -> bool:
        return self.x == "?"

    @property
    def staged(self) -> bool:
        return not self.conflicted and not self.untracked and self.x not in " !"

    @property
    def unstaged(self) -> bool:
        return self.conflicted or self.untracked or self.y not in " !"


@dataclass
class Ref:
    name: str
    full: str
    sha: str
    kind: str  # local | remote | tag
    upstream: str = ""
    track: str = ""
    is_head: bool = False
    subject: str = ""
    date: int = 0

    @property
    def remote(self) -> str:
        return self.name.split("/", 1)[0] if self.kind == "remote" else ""

    @property
    def branch_on_remote(self) -> str:
        return self.name.split("/", 1)[1] if self.kind == "remote" and "/" in self.name else self.name


@dataclass
class Worktree:
    path: str
    head: str = ""
    branch: str = ""
    bare: bool = False
    detached: bool = False
    locked: bool = False


@dataclass
class Submodule:
    path: str
    sha: str
    state: str  # " " ok, "-" not initialized, "+" changed, "U" conflict
    describe: str = ""


@dataclass
class RepoState:
    merging: bool = False
    rebasing: bool = False
    cherry_picking: bool = False
    reverting: bool = False
    bisecting: bool = False

    @property
    def kind(self) -> str:
        for k in ("rebasing", "merging", "cherry_picking", "reverting"):
            if getattr(self, k):
                return k
        return ""
