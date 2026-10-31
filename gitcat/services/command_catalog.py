"""Declarative catalogue of git commands for the Command Center.

Each Command is a fixed argv prefix plus Fields. A Field turns the user's input into argv tokens:
  flag     checkbox → `flag`
  text     value → `flag=value` if flag ends with "=", `flag value` if flag set, positional otherwise
  int      like text, validated as integer
  choice   value picked from `choices` (positional or with flag)
  ref      revision picker (branches/tags/commits), otherwise like text
  remote   remote-name picker
  paths    space-separated paths placed after `--`
  multi    space-separated values (e.g. several commits), positional
"""
from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Field:
    kind: str
    flag: str = ""
    label: str = ""
    default: object = None
    choices: tuple[str, ...] = ()
    required: bool = False
    hint: str = ""

    @property
    def title(self) -> str:
        return self.label or self.flag or self.kind


@dataclass(frozen=True)
class Command:
    id: str
    group: str
    args: tuple[str, ...]
    desc: str
    fields: tuple[Field, ...] = ()
    danger: bool = False
    network: bool = False
    needs_repo: bool = True
    doc: str = ""

    @property
    def doc_url(self) -> str:
        return f"https://git-scm.com/docs/git-{self.doc or self.args[0]}"


def F(kind: str, flag: str = "", label: str = "", default=None, choices=(), required=False, hint=""):  # noqa: N802
    return Field(kind, flag, label, default, tuple(choices), required, hint)


def flag(f: str, label: str = "", default=False):
    return F("flag", f, label, default)


def build_argv(cmd: Command, values: dict[str, object]) -> list[str]:
    """values: field index (as str) -> bool/str. Raises ValueError for missing required values."""
    argv = list(cmd.args)
    tail: list[str] = []
    for i, fd in enumerate(cmd.fields):
        v = values.get(str(i))
        if fd.kind == "flag":
            if v:
                argv.extend(shlex.split(fd.flag))
            continue
        s = str(v).strip() if v is not None else ""
        if not s:
            if fd.required:
                raise ValueError(fd.title)
            continue
        if fd.kind == "int" and not s.lstrip("-").isdigit():
            raise ValueError(fd.title)
        if fd.kind == "paths":
            tail.extend(shlex.split(s, posix=True))
        elif fd.kind == "multi":
            argv.extend(shlex.split(s, posix=True))
        elif fd.flag.endswith("="):
            argv.append(fd.flag + s)
        elif fd.flag:
            argv.extend([fd.flag, s])
        else:
            argv.append(s)
    if tail:
        argv += ["--", *tail]
    return argv


def preview(argv: list[str]) -> str:
    return "git " + " ".join(shlex.quote(a) if any(c in a for c in " \"'$&|<>;*?") or not a else a for a in argv)


SCOPE = F("choice", "", "scope", "", ("", "--local", "--global", "--system", "--worktree"))

CATALOG: list[Command] = [
    # ------------------------------------------------------------------ setup & config
    Command("init", "setup", ("init",), "Create an empty repository (runs in the chosen folder)",
            (F("path", "", "directory", required=True), F("text", "--initial-branch=", "initial branch", "main"),
             flag("--bare")), needs_repo=False),
    Command("clone", "setup", ("clone", "--progress"), "Clone a repository into a new directory",
            (F("text", "", "url", required=True), F("path", "", "directory"), F("text", "--branch", "branch"),
             F("int", "--depth", "depth"), flag("--recurse-submodules"), flag("--single-branch"), flag("--bare"),
             flag("--mirror"), F("text", "--filter=", "filter", hint="blob:none")), network=True, needs_repo=False),
    Command("config-list", "setup", ("config", "--list", "--show-origin"), "List configuration with origins",
            (SCOPE,), needs_repo=False, doc="config"),
    Command("config-get", "setup", ("config", "--get-all"), "Read a configuration value",
            (SCOPE, F("text", "", "key", required=True, hint="user.email")), needs_repo=False, doc="config"),
    Command("config-set", "setup", ("config",), "Set a configuration value",
            (SCOPE, F("text", "", "key", required=True), F("text", "", "value", required=True)), needs_repo=False,
            doc="config"),
    Command("config-unset", "setup", ("config", "--unset-all"), "Remove a configuration value",
            (SCOPE, F("text", "", "key", required=True)), needs_repo=False, doc="config"),
    Command("version", "setup", ("version", "--build-options"), "Git version and build options", needs_repo=False),
    Command("var", "setup", ("var", "-l"), "Show git logical variables"),

    # ------------------------------------------------------------------ snapshot
    Command("status", "snapshot", ("status",), "Working tree status",
            (flag("--short"), flag("--branch"), flag("--ignored"), flag("--untracked-files=all", "untracked=all"),
             F("paths", "", "paths"))),
    Command("add", "snapshot", ("add",), "Add file contents to the index",
            (F("paths", "", "paths", "."), flag("--all"), flag("--update"), flag("--intent-to-add"), flag("--force"),
             flag("--renormalize"), flag("--dry-run"))),
    Command("diff", "snapshot", ("diff",), "Show changes",
            (F("ref", "", "commit A"), F("ref", "", "commit B"), flag("--cached"), flag("--stat"), flag("--name-status"),
             flag("--word-diff"), flag("--ignore-all-space"), flag("--find-renames"), F("paths", "", "paths"))),
    Command("commit", "snapshot", ("commit",), "Record changes",
            (F("text", "-m", "message"), flag("--all"), flag("--amend"), flag("--no-edit"), flag("--allow-empty"),
             flag("--signoff"), flag("--no-verify"), flag("-S", "GPG sign"), F("ref", "--fixup=", "fixup commit"),
             F("text", "--author=", "author", hint="Name <mail>"), F("text", "--date=", "date"))),
    Command("restore", "snapshot", ("restore",), "Restore working tree files",
            (F("paths", "", "paths", required=True), F("ref", "--source=", "source"), flag("--staged"),
             flag("--worktree"))),
    Command("reset", "snapshot", ("reset",), "Reset HEAD / index / working tree",
            (F("choice", "", "mode", "--mixed", ("--soft", "--mixed", "--hard", "--merge", "--keep")),
             F("ref", "", "target", "HEAD"), F("paths", "", "paths")), danger=True),
    Command("rm", "snapshot", ("rm",), "Remove files from the working tree and index",
            (F("paths", "", "paths", required=True), flag("--cached"), flag("-r"), flag("--force"), flag("--dry-run")),
            danger=True),
    Command("mv", "snapshot", ("mv",), "Move or rename a file or directory",
            (F("text", "", "source", required=True), F("text", "", "destination", required=True), flag("--force"),
             flag("--dry-run"))),
    Command("clean", "snapshot", ("clean",), "Remove untracked files",
            (flag("--dry-run", default=True), flag("--force"), flag("-d", "directories"), flag("-x", "ignored too"),
             flag("-X", "only ignored"), F("paths", "", "paths")), danger=True),
    Command("notes", "snapshot", ("notes",), "Add or inspect object notes",
            (F("choice", "", "action", "list", ("list", "add", "append", "show", "remove", "prune")),
             F("text", "-m", "message"), flag("--force"), F("ref", "", "object"))),

    # ------------------------------------------------------------------ branches
    Command("branch-list", "branch", ("branch", "-vv"), "List branches",
            (flag("--all"), flag("--remotes"), F("ref", "--merged", "merged into"), F("ref", "--no-merged", "not merged into"),
             F("ref", "--contains", "contains commit"), F("text", "--sort=", "sort", "-committerdate"),
             F("text", "--list", "pattern")), doc="branch"),
    Command("branch-create", "branch", ("branch",), "Create a branch",
            (F("text", "", "name", required=True), F("ref", "", "start point"), F("text", "--track=", "track",
                                                                                   hint="direct|inherit"), flag("--force")),
            doc="branch"),
    Command("branch-delete", "branch", ("branch",), "Delete branches",
            (F("choice", "", "mode", "-d", ("-d", "-D")), F("multi", "", "branches", required=True), flag("--remotes")),
            danger=True, doc="branch"),
    Command("branch-move", "branch", ("branch", "-m"), "Rename a branch",
            (F("text", "", "old"), F("text", "", "new", required=True), flag("--force")), doc="branch"),
    Command("branch-upstream", "branch", ("branch",), "Set or remove upstream",
            (F("ref", "--set-upstream-to=", "upstream"), flag("--unset-upstream"), F("text", "", "branch")),
            doc="branch"),
    Command("switch", "branch", ("switch",), "Switch branches",
            (F("ref", "", "branch"), F("text", "--create", "create"), F("text", "--force-create", "force create"),
             flag("--detach"), F("text", "--orphan", "orphan"), flag("--discard-changes"), flag("--merge"),
             flag("--guess"))),
    Command("checkout", "branch", ("checkout",), "Checkout a branch, commit or paths",
            (F("ref", "", "target"), F("text", "-b", "new branch"), flag("--detach"), F("text", "--orphan", "orphan"),
             flag("--force"), flag("--ours"), flag("--theirs"), F("paths", "", "paths"))),
    Command("merge", "branch", ("merge",), "Join histories",
            (F("multi", "", "branches / commits"), flag("--no-ff"), flag("--ff-only"), flag("--squash"),
             flag("--no-commit"), flag("--allow-unrelated-histories"), F("choice", "--strategy=", "strategy", "",
                                                                        ("", "ort", "recursive", "resolve", "octopus",
                                                                         "ours", "subtree")),
             F("text", "-X", "strategy option", hint="theirs | ours | ignore-space-change"), F("text", "-m", "message"),
             flag("--abort"), flag("--continue"), flag("--quit"))),
    Command("rebase", "branch", ("rebase",), "Reapply commits on top of another base",
            (F("ref", "", "upstream"), F("ref", "--onto", "onto"), flag("--autostash"), flag("--autosquash"),
             flag("--rebase-merges"), flag("--update-refs"), flag("--keep-base"), flag("--root"),
             flag("--committer-date-is-author-date"), F("text", "--exec", "exec"), flag("--abort"), flag("--continue"),
             flag("--skip"), flag("--quit"))),
    Command("cherry-pick", "branch", ("cherry-pick",), "Apply existing commits",
            (F("multi", "", "commits / ranges"), flag("-x", "record origin"), flag("--no-commit"), flag("--signoff"),
             F("int", "-m", "mainline parent"), flag("--allow-empty"), flag("--abort"), flag("--continue"),
             flag("--skip"))),
    Command("revert", "branch", ("revert",), "Revert existing commits",
            (F("multi", "", "commits / ranges"), flag("--no-edit"), flag("--no-commit"), F("int", "-m", "mainline parent"),
             flag("--abort"), flag("--continue"), flag("--skip"))),
    Command("tag-list", "branch", ("tag",), "List tags",
            (F("text", "--list", "pattern"), F("int", "-n", "message lines"), F("ref", "--contains", "contains"),
             F("ref", "--merged", "merged"), F("text", "--sort=", "sort", "-v:refname")), doc="tag"),
    Command("tag-create", "branch", ("tag",), "Create a tag",
            (F("text", "", "name", required=True), F("ref", "", "commit"), flag("--annotate"), F("text", "-m", "message"),
             flag("--sign"), flag("--force")), doc="tag"),
    Command("tag-delete", "branch", ("tag", "--delete"), "Delete local tags",
            (F("multi", "", "tags", required=True),), danger=True, doc="tag"),
    Command("tag-verify", "branch", ("tag", "--verify"), "Verify tag signatures",
            (F("multi", "", "tags", required=True),), doc="tag"),
    Command("stash", "branch", ("stash",), "Stash operations",
            (F("choice", "", "action", "list", ("list", "show", "push", "pop", "apply", "drop", "clear", "branch",
                                                  "create")),
             F("text", "", "stash / branch", hint="stash@{0}"), F("text", "-m", "message"), flag("--include-untracked"),
             flag("--keep-index"), flag("--staged"), flag("--index"), flag("-p", "patch (show)"))),
    Command("worktree", "branch", ("worktree",), "Manage worktrees",
            (F("choice", "", "action", "list", ("list", "add", "lock", "unlock", "move", "remove", "prune", "repair")),
             F("text", "", "path"), F("text", "", "branch / new path"), F("text", "-b", "new branch"),
             flag("--force"), flag("--detach"), flag("--porcelain"))),
    Command("sparse-checkout", "branch", ("sparse-checkout",), "Sparse checkout",
            (F("choice", "", "action", "list", ("list", "init", "set", "add", "reapply", "disable")), flag("--cone"),
             flag("--no-cone"), F("multi", "", "patterns / dirs"))),

    # ------------------------------------------------------------------ remotes
    Command("fetch", "remote", ("fetch", "--progress"), "Download objects and refs",
            (F("remote", "", "remote"), F("multi", "", "refspecs"), flag("--all"), flag("--prune"), flag("--prune-tags"),
             flag("--tags"), flag("--no-tags"), F("int", "--depth", "depth"), flag("--unshallow"), flag("--dry-run"),
             flag("--force")), network=True, danger=False),
    Command("pull", "remote", ("pull", "--progress"), "Fetch and integrate",
            (F("remote", "", "remote"), F("text", "", "branch"), F("choice", "", "mode", "", ("", "--rebase",
                                                                                            "--no-rebase", "--ff-only")),
             flag("--autostash"), flag("--squash"), flag("--no-commit"), flag("--allow-unrelated-histories")),
            network=True),
    Command("push", "remote", ("push", "--progress"), "Update remote refs",
            (F("remote", "", "remote"), F("multi", "", "refspecs", hint="main  v1.0.0  HEAD:refs/heads/x"),
             flag("--set-upstream"), flag("--force-with-lease"), flag("--force-if-includes"), flag("--force"),
             flag("--tags"), flag("--follow-tags"), flag("--all"), flag("--mirror"), flag("--delete"), flag("--atomic"),
             flag("--no-verify"), flag("--dry-run"), F("text", "--push-option=", "push option", hint="ci.skip")),
            network=True, danger=True),
    Command("remote", "remote", ("remote",), "Manage remotes",
            (F("choice", "", "action", "-v", ("-v", "add", "remove", "rename", "set-url", "get-url", "show", "prune",
                                                "update", "set-head", "set-branches")),
             F("text", "", "name"), F("text", "", "url / new name"), flag("--push"), flag("--add"),
             flag("--dry-run"), F("text", "-t", "track branch"))),
    Command("ls-remote", "remote", ("ls-remote",), "List references in a remote",
            (F("remote", "", "remote / url"), flag("--heads"), flag("--tags"), flag("--symref"),
             F("text", "", "pattern")), network=True),
    Command("submodule", "remote", ("submodule",), "Submodules",
            (F("choice", "", "action", "status", ("status", "init", "update", "sync", "deinit", "add", "summary",
                                                    "foreach", "set-url", "set-branch", "absorbgitdirs")),
             flag("--init"), flag("--recursive"), flag("--remote"), flag("--force"), flag("--all"),
             F("text", "", "url / command"), F("text", "", "path"))),

    # ------------------------------------------------------------------ inspection
    Command("log", "inspect", ("log",), "Show commit logs",
            (F("ref", "", "range", hint="main..feature"), F("int", "-n", "max count", 50), flag("--oneline"),
             flag("--graph"), flag("--decorate"), flag("--all"), flag("--stat"), flag("-p", "patch"), flag("--first-parent"),
             flag("--no-merges"), F("text", "--author=", "author"), F("text", "--since=", "since", hint="2 weeks ago"),
             F("text", "--until=", "until"), F("text", "--grep=", "grep"), F("text", "-S", "pickaxe"),
             F("text", "-G", "regex in diff"), F("text", "--format=", "format", hint="%h %an %s"), flag("--follow"),
             F("paths", "", "paths"))),
    Command("show", "inspect", ("show",), "Show objects",
            (F("ref", "", "object", "HEAD"), flag("--stat"), flag("--name-status"), flag("--no-patch"),
             F("text", "--format=", "format"))),
    Command("shortlog", "inspect", ("shortlog", "HEAD"), "Summarise log by author",
            (flag("-s", "summary"), flag("-n", "sort by count"), flag("-e", "email"), flag("--all"),
             F("text", "--since=", "since"))),
    Command("describe", "inspect", ("describe",), "Name a commit from the nearest tag",
            (F("ref", "", "commit"), flag("--tags"), flag("--always"), flag("--long"), flag("--dirty"),
             flag("--contains"), F("text", "--match=", "match"))),
    Command("blame", "inspect", ("blame",), "Who changed each line",
            (F("text", "", "file", required=True), F("text", "-L", "range", hint="10,40"), F("ref", "", "revision"),
             flag("-w", "ignore whitespace"), flag("-M", "detect moves"), flag("-C", "detect copies"), flag("-e"))),
    Command("grep", "inspect", ("grep", "-n"), "Search tracked content",
            (F("text", "-e", "pattern", required=True), F("ref", "", "revision"), flag("-i", "ignore case"),
             flag("-w", "word"), flag("-E", "extended regex"), flag("--untracked"), flag("--count"), flag("-l", "names only"),
             F("paths", "", "paths"))),
    Command("reflog", "inspect", ("reflog",), "Reference logs",
            (F("choice", "", "action", "show", ("show", "list", "exists", "expire", "delete")), F("text", "", "ref"),
             F("int", "-n", "count", 100), F("text", "--expire=", "expire", hint="90.days.ago"), flag("--all"),
             flag("--dry-run"))),
    Command("cherry", "inspect", ("cherry", "-v"), "Commits not yet applied upstream",
            (F("ref", "", "upstream"), F("ref", "", "head"))),
    Command("range-diff", "inspect", ("range-diff",), "Compare two commit ranges",
            (F("text", "", "range 1", required=True, hint="main..old"), F("text", "", "range 2", required=True,
                                                                          hint="main..new"))),
    Command("merge-base", "inspect", ("merge-base",), "Common ancestor",
            (F("multi", "", "commits", required=True), flag("--all"), flag("--is-ancestor"), flag("--fork-point"))),
    Command("rev-list", "inspect", ("rev-list",), "List / count commits",
            (F("text", "", "range", "HEAD"), flag("--count"), flag("--left-right"), flag("--all"), flag("--objects"),
             F("int", "--max-count=", "max"))),
    Command("rev-parse", "inspect", ("rev-parse",), "Parse revisions / repository info",
            (F("text", "", "revision", "HEAD"), flag("--short"), flag("--abbrev-ref"), flag("--symbolic-full-name"),
             flag("--show-toplevel"), flag("--git-dir"), flag("--is-shallow-repository"))),
    Command("name-rev", "inspect", ("name-rev",), "Symbolic names for revisions",
            (F("multi", "", "commits", "HEAD"), flag("--tags"), flag("--name-only"))),
    Command("cat-file", "inspect", ("cat-file",), "Object content / type / size",
            (F("choice", "", "mode", "-p", ("-p", "-t", "-s", "-e")), F("text", "", "object", required=True,
                                                                      hint="HEAD:README.md"))),
    Command("ls-files", "inspect", ("ls-files",), "Files in the index / working tree",
            (flag("--others"), flag("--ignored"), flag("--exclude-standard"), flag("--stage"), flag("--unmerged"),
             flag("--deleted"), flag("--modified"), F("paths", "", "paths"))),
    Command("ls-tree", "inspect", ("ls-tree",), "List a tree object",
            (F("ref", "", "tree-ish", "HEAD"), flag("-r", "recursive"), flag("--name-only"), flag("-l", "sizes"),
             F("paths", "", "paths"))),
    Command("for-each-ref", "inspect", ("for-each-ref",), "Output ref information",
            (F("text", "--format=", "format", "%(refname:short) %(objectname:short) %(committerdate:relative)"),
             F("text", "--sort=", "sort", "-committerdate"), F("int", "--count=", "count"),
             F("text", "", "pattern", "refs/heads"))),
    Command("count-objects", "inspect", ("count-objects", "-vH"), "Repository object statistics"),
    Command("check-ignore", "inspect", ("check-ignore", "-v", "--no-index"), "Explain why a path is ignored",
            (F("multi", "", "paths", required=True),)),
    Command("check-attr", "inspect", ("check-attr", "-a"), "Show gitattributes for paths",
            (F("multi", "", "paths", required=True),)),
    Command("verify-commit", "inspect", ("verify-commit", "-v"), "Verify commit signatures",
            (F("multi", "", "commits", "HEAD"),)),
    Command("bisect", "inspect", ("bisect",), "Binary search for a bad commit",
            (F("choice", "", "action", "log", ("start", "good", "bad", "skip", "reset", "log", "run", "terms",
                                                 "visualize")),
             F("multi", "", "commits / script"))),

    # ------------------------------------------------------------------ patches & archives
    Command("format-patch", "patch", ("format-patch",), "Prepare patches for e-mail",
            (F("text", "", "range", required=True, hint="-3  or  main..feature"), F("text", "-o", "output dir"),
             flag("--cover-letter"), flag("--stdout"), F("int", "-v", "reroll count"), flag("--signoff"))),
    Command("am", "patch", ("am",), "Apply mailbox patches",
            (F("multi", "", "patch files"), flag("-3", "3-way"), flag("--signoff"), flag("--keep-cr"), flag("--abort"),
             flag("--continue"), flag("--skip"))),
    Command("apply", "patch", ("apply",), "Apply a patch",
            (F("multi", "", "patch files", required=True), flag("--check"), flag("--stat"), flag("--index"),
             flag("--cached"), flag("--3way"), flag("-R", "reverse"), flag("--reject"))),
    Command("archive", "patch", ("archive",), "Create an archive of a tree",
            (F("choice", "--format=", "format", "zip", ("zip", "tar", "tar.gz", "tgz")), F("text", "-o", "output file",
                                                                                         required=True),
             F("text", "--prefix=", "prefix", hint="project/"), F("ref", "", "tree-ish", "HEAD"), F("paths", "", "paths"))),
    Command("bundle", "patch", ("bundle",), "Move objects and refs by archive",
            (F("choice", "", "action", "create", ("create", "verify", "list-heads", "unbundle")),
             F("text", "", "file", required=True), F("multi", "", "refs / range", hint="--all"))),
    Command("request-pull", "patch", ("request-pull",), "Summarise pending changes",
            (F("ref", "", "start", required=True), F("text", "", "url", required=True), F("ref", "", "end"))),

    # ------------------------------------------------------------------ maintenance
    Command("gc", "maint", ("gc",), "Cleanup and optimise the repository",
            (flag("--aggressive"), F("text", "--prune=", "prune", hint="now / 2.weeks.ago"), flag("--auto"))),
    Command("fsck", "maint", ("fsck",), "Verify object connectivity",
            (flag("--full"), flag("--unreachable"), flag("--lost-found"), flag("--no-reflogs"), flag("--dangling"))),
    Command("prune", "maint", ("prune",), "Prune unreachable objects",
            (flag("--dry-run", default=True), flag("--verbose"), F("text", "--expire=", "expire")), danger=True),
    Command("repack", "maint", ("repack",), "Pack unpacked objects",
            (flag("-a", "all"), flag("-d", "delete redundant"), flag("--write-bitmap-index"), flag("-f"))),
    Command("maintenance", "maint", ("maintenance",), "Background maintenance",
            (F("choice", "", "action", "run", ("run", "start", "stop", "register", "unregister")),
             F("choice", "--task=", "task", "", ("", "gc", "commit-graph", "prefetch", "loose-objects",
                                                 "incremental-repack", "pack-refs")))),
    Command("commit-graph", "maint", ("commit-graph", "write", "--reachable"), "Write the commit-graph file",
            (flag("--changed-paths"),)),
    Command("pack-refs", "maint", ("pack-refs",), "Pack refs", (flag("--all"), flag("--prune"))),
    Command("rerere", "maint", ("rerere",), "Reuse recorded conflict resolutions",
            (F("choice", "", "action", "status", ("status", "diff", "remaining", "clear", "forget", "gc")),
             F("paths", "", "paths"))),
    Command("lfs", "maint", ("lfs",), "Git LFS (requires git-lfs)",
            (F("choice", "", "action", "status", ("status", "install", "track", "untrack", "ls-files", "pull", "push",
                                                    "fetch", "prune", "migrate", "env", "locks", "lock", "unlock")),
             F("multi", "", "args", hint="\"*.psd\"  or  info --everything"))),
    Command("replace", "maint", ("replace",), "Replace objects",
            (F("text", "", "object"), F("text", "", "replacement"), flag("--list"), flag("--delete"), flag("--force"))),
]

GROUPS = ["setup", "snapshot", "branch", "remote", "inspect", "patch", "maint"]


def by_id(cmd_id: str) -> Optional[Command]:
    return next((c for c in CATALOG if c.id == cmd_id), None)


@dataclass
class History:
    items: list[str] = field(default_factory=list)

    def add(self, line: str, limit: int = 100):
        if line in self.items:
            self.items.remove(line)
        self.items.insert(0, line)
        del self.items[limit:]
