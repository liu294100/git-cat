"""Repository facade: every git query and command goes through the git CLI."""
from __future__ import annotations

import datetime as _dt
import os
import shlex
import tempfile
from typing import Iterable, Optional

from .models import Commit, FileChange, Ref, RepoState, Submodule, Worktree
from .runner import GitError, Logger, Progress, decode, run_git, run_git_stream
from .versioning import SEMVER_RE, semver_key


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


class Repo:
    def __init__(self, path: str, logger: Optional[Logger] = None):
        root = Repo.find_root(path)
        if not root:
            raise GitError(["rev-parse"], 128, "", f"Not a git repository: {path}")
        self.path = os.path.normpath(root)
        self.logger = logger
        self._git_dir: Optional[str] = None

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    # ------------------------------------------------------------------ basics
    @staticmethod
    def find_root(path: str) -> Optional[str]:
        if not path or not os.path.isdir(path):
            return None
        try:
            code, out, _ = run_git(["rev-parse", "--show-toplevel"], path)
        except (OSError, NotADirectoryError):
            return None
        return decode(out).strip() if code == 0 else None

    @staticmethod
    def clone(url: str, dest: str, logger: Optional[Logger] = None, depth: int = 0,
              branch: str = "", recursive: bool = False, progress: Optional[Progress] = None) -> str:
        parent = os.path.dirname(os.path.abspath(dest)) or "."
        os.makedirs(parent, exist_ok=True)
        args = ["clone", "--progress"]
        if depth:
            args.append(f"--depth={depth}")
        if branch:
            args += ["-b", branch]
        if recursive:
            args.append("--recurse-submodules")
        args += [url, dest]
        code, o, e = run_git_stream(args, parent, progress)
        if logger:
            logger("git " + " ".join(args), code, o, e)
        if code != 0:
            raise GitError(args, code, o, e)
        return dest

    @staticmethod
    def init(path: str, branch: str = "main") -> str:
        os.makedirs(path, exist_ok=True)
        code, out, err = run_git(["init", "-b", branch], path)
        if code != 0:
            code, out, err = run_git(["init"], path)
        if code != 0:
            raise GitError(["init"], code, decode(out), decode(err))
        return path

    def run_bytes(self, *args: str, input: Optional[bytes] = None, check: bool = True) -> bytes:
        code, out, err = run_git(list(args), self.path, input)
        if check and code != 0:
            raise GitError(list(args), code, decode(out), decode(err))
        return out

    def run(self, *args: str, input: Optional[str] = None, check: bool = True) -> str:
        code, out, err = run_git(list(args), self.path, input.encode("utf-8") if input is not None else None)
        o, e = decode(out), decode(err)
        if check and code != 0:
            raise GitError(list(args), code, o, e)
        return o

    def do(self, *args: str, input: Optional[str] = None, env: Optional[dict] = None) -> str:
        """Run a mutating command: log it and return stdout+stderr."""
        code, out, err = run_git(list(args), self.path,
                              input.encode("utf-8") if input is not None else None, env)
        o, e = decode(out), decode(err)
        if self.logger:
            self.logger("git " + " ".join(args), code, o, e)
        if code != 0:
            raise GitError(list(args), code, o, e)
        return (o + ("\n" if o and e else "") + e).strip()

    def do_stream(self, *args: str, progress: Optional[Progress] = None) -> str:
        code, o, e = run_git_stream(list(args), self.path, progress)
        if self.logger:
            self.logger("git " + " ".join(args), code, o, e)
        if code != 0:
            raise GitError(list(args), code, o, e)
        return (o + ("\n" if o and e else "") + e).strip()

    @property
    def git_dir(self) -> str:
        if not self._git_dir:
            self._git_dir = self.run("rev-parse", "--absolute-git-dir").strip()
        return self._git_dir

    # ------------------------------------------------------------------ queries
    def has_commits(self) -> bool:
        return bool(self.run("rev-parse", "--verify", "-q", "HEAD", check=False).strip())

    def current_branch(self) -> Optional[str]:
        b = self.run("symbolic-ref", "--short", "-q", "HEAD", check=False).strip()
        return b or None

    def head_sha(self) -> str:
        return self.run("rev-parse", "--verify", "-q", "HEAD", check=False).strip()

    def rev_parse(self, ref: str) -> str:
        return self.run("rev-parse", "--verify", "-q", ref + "^{commit}", check=False).strip()

    def upstream(self, branch: Optional[str] = None) -> str:
        spec = f"{branch}@{{upstream}}" if branch else "@{upstream}"
        return self.run("rev-parse", "--abbrev-ref", spec, check=False).strip()

    def ahead_behind(self) -> tuple[int, int]:
        out = self.run("rev-list", "--left-right", "--count", "@{upstream}...HEAD", check=False).split()
        if len(out) == 2:
            return int(out[1]), int(out[0])
        return 0, 0

    def state(self) -> RepoState:
        g = self.git_dir
        ex = lambda n: os.path.exists(os.path.join(g, n))  # noqa: E731
        return RepoState(
            merging=ex("MERGE_HEAD"),
            rebasing=ex("rebase-merge") or ex("rebase-apply"),
            cherry_picking=ex("CHERRY_PICK_HEAD"),
            reverting=ex("REVERT_HEAD"),
            bisecting=ex("BISECT_LOG"),
        )

    def status(self) -> list[FileChange]:
        out = self.run("status", "--porcelain=v1", "-z", "--untracked-files=all")
        parts = out.split("\0")
        res: list[FileChange] = []
        i = 0
        while i < len(parts):
            e = parts[i]
            i += 1
            if len(e) < 4:
                continue
            x, y, p = e[0], e[1], e[3:]
            orig = ""
            if x in "RC" or y in "RC":
                orig = parts[i] if i < len(parts) else ""
                i += 1
            res.append(FileChange(p, x, y, orig))
        return res

    def refs(self) -> list[Ref]:
        fmt = ("%(refname)%1f%(objectname)%1f%(upstream:short)%1f%(upstream:track)%1f%(HEAD)%1f"
               "%(contents:subject)%1f%(*objectname)%1f%(creatordate:unix)")
        out = self.run("for-each-ref", f"--format={fmt}", "refs/heads", "refs/remotes", "refs/tags")
        res: list[Ref] = []
        for line in out.splitlines():
            f = line.split("\x1f")
            if len(f) < 8:
                continue
            full, sha, up, track, head, subj, peeled, date = f[:8]
            d = int(date) if date.isdigit() else 0
            if full.startswith("refs/heads/"):
                res.append(Ref(full[11:], full, sha, "local", up, track, head == "*", subj, d))
            elif full.startswith("refs/remotes/"):
                if full.endswith("/HEAD"):
                    continue
                res.append(Ref(full[13:], full, sha, "remote", subject=subj, date=d))
            elif full.startswith("refs/tags/"):
                res.append(Ref(full[10:], full, peeled or sha, "tag", subject=subj, date=d))
        return res

    def remotes(self) -> dict[str, str]:
        res: dict[str, str] = {}
        for line in self.run("remote", "-v").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] not in res:
                res[parts[0]] = parts[1]
        return res

    def stashes(self) -> list[tuple[str, str, str]]:
        out = self.run("stash", "list", "--format=%gd%x1f%s%x1f%cr", check=False)
        res = []
        for line in out.splitlines():
            f = line.split("\x1f")
            if len(f) == 3:
                res.append((f[0], f[1], f[2]))
        return res

    def worktrees(self) -> list[Worktree]:
        out = self.run("worktree", "list", "--porcelain", check=False)
        res: list[Worktree] = []
        cur: Optional[Worktree] = None
        for line in out.splitlines():
            if line.startswith("worktree "):
                cur = Worktree(os.path.normpath(line[9:]))
                res.append(cur)
            elif cur is None:
                continue
            elif line.startswith("HEAD "):
                cur.head = line[5:]
            elif line.startswith("branch "):
                cur.branch = line[7:].removeprefix("refs/heads/")
            elif line == "bare":
                cur.bare = True
            elif line == "detached":
                cur.detached = True
            elif line.startswith("locked"):
                cur.locked = True
        return res

    def submodules(self) -> list[Submodule]:
        if not os.path.exists(os.path.join(self.path, ".gitmodules")):
            return []
        out = self.run("submodule", "status", check=False)
        res = []
        for line in out.splitlines():
            if len(line) < 42:
                continue
            state, rest = line[0], line[1:].split()
            if len(rest) >= 2:
                res.append(Submodule(rest[1], rest[0], state, " ".join(rest[2:]).strip("()")))
        return res

    LOG_FMT = "%H%x1f%P%x1f%an%x1f%ae%x1f%at%x1f%s%x1f%D%x1e"

    def _parse_log(self, out: str) -> list[Commit]:
        res: list[Commit] = []
        for rec in out.split("\x1e"):
            rec = rec.strip("\n")
            if not rec:
                continue
            f = rec.split("\x1f")
            if len(f) < 7:
                continue
            refs = [r.strip() for r in f[6].split(",") if r.strip()]
            res.append(Commit(f[0], f[1].split(), f[2], f[3], int(f[4] or 0), f[5], refs))
        return res

    def log(self, max_count: int = 2000, all_refs: bool = True, path: Optional[str] = None,
            rev_range: str = "") -> list[Commit]:
        if not self.has_commits():
            return []
        args = ["log", f"--format={self.LOG_FMT}", f"--max-count={max_count}"]
        if rev_range:
            args.append(rev_range)
        elif path:
            args += ["--follow", "--", path]
        else:
            args.append("--date-order")
            if all_refs:
                args += ["--branches", "--remotes", "--tags", "HEAD"]
        return self._parse_log(self.run(*args))

    def search_log(self, query: str, mode: str, max_count: int = 500) -> list[Commit]:
        """mode: message | author | content (pickaxe -S) | path"""
        if not self.has_commits() or not query:
            return []
        args = ["log", f"--format={self.LOG_FMT}", f"--max-count={max_count}", "--branches", "--remotes", "--tags",
                "HEAD"]
        if mode == "message":
            args += ["-i", f"--grep={query}"]
        elif mode == "author":
            args += ["-i", f"--author={query}"]
        elif mode == "content":
            args += [f"-S{query}"]
        elif mode == "path":
            args += ["--", f"*{query}*"]
        return self._parse_log(self.run(*args, check=False))

    def commit_info(self, sha: str) -> dict:
        out = self.run("show", "-s", "--format=%H%x1f%P%x1f%an%x1f%ae%x1f%ai%x1f%cn%x1f%ce%x1f%ci%x1f%B", sha)
        f = out.split("\x1f", 8)
        keys = ["sha", "parents", "author", "email", "date", "committer", "cemail", "cdate", "body"]
        info = dict(zip(keys, f))
        info["parents"] = info.get("parents", "").split()
        info["contains"] = self.run("describe", "--contains", "--always", sha, check=False).strip()
        return info

    def _parse_name_status(self, out: str) -> list[FileChange]:
        parts = out.split("\0")
        res: list[FileChange] = []
        i = 0
        while i < len(parts):
            st = parts[i]
            i += 1
            if not st:
                continue
            code = st[0]
            if code in "RC":
                if i + 1 >= len(parts):
                    break
                old, new = parts[i], parts[i + 1]
                i += 2
                res.append(FileChange(new, code, " ", old))
            else:
                if i >= len(parts):
                    break
                res.append(FileChange(parts[i], code, " "))
                i += 1
        return res

    def commit_files(self, sha: str, parents: list[str]) -> list[FileChange]:
        if parents:
            out = self.run("diff", "--name-status", "-z", "-M", parents[0], sha)
        else:
            out = self.run("diff-tree", "--root", "--no-commit-id", "-r", "--name-status", "-z", "-M", sha)
        return self._parse_name_status(out)

    def range_files(self, a: str, b: str) -> list[FileChange]:
        return self._parse_name_status(self.run("diff", "--name-status", "-z", "-M", a, b))

    def numstat(self, a: str, b: str) -> tuple[int, int]:
        add = rem = 0
        for line in self.run("diff", "--numstat", a, b, check=False).splitlines():
            p = line.split("\t")
            if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
                add += int(p[0])
                rem += int(p[1])
        return add, rem

    @staticmethod
    def _diff_opts(context: int, ignore_ws: bool) -> list[str]:
        opts = [f"-U{context}", "--no-color", "--no-ext-diff"]
        if ignore_ws:
            opts.append("-w")
        return opts

    def diff_file(self, fc: FileChange, staged: bool, context: int = 3, ignore_ws: bool = False) -> bytes:
        opts = self._diff_opts(context, ignore_ws)
        if fc.untracked:
            out = self.run_bytes("diff", "--no-index", *opts, "--", "/dev/null", fc.path, check=False)
            if not out.strip():
                full = os.path.join(self.path, fc.path)
                if os.path.isdir(full):
                    return b"(directory)"
            return out
        paths = [fc.orig_path, fc.path] if (staged and fc.orig_path) else [fc.path]
        args = ["diff", *opts, "-M"] + (["--cached"] if staged else []) + ["--", *paths]
        return self.run_bytes(*args, check=False)

    def commit_diff(self, sha: str, parents: list[str], fc: Optional[FileChange] = None,
                    context: int = 3, ignore_ws: bool = False) -> bytes:
        base = parents[0] if parents else EMPTY_TREE
        return self.range_diff(base, sha, fc, context, ignore_ws)

    def range_diff(self, a: str, b: str, fc: Optional[FileChange] = None,
                   context: int = 3, ignore_ws: bool = False) -> bytes:
        args = ["diff", *self._diff_opts(context, ignore_ws), "-M", a]
        if b:
            args.append(b)
        if fc:
            args += ["--", *([fc.orig_path, fc.path] if fc.orig_path else [fc.path])]
        return self.run_bytes(*args, check=False)

    def stash_files(self, ref: str) -> list[FileChange]:
        files = self._parse_name_status(self.run("stash", "show", "--name-status", "-z", ref, check=False))
        untracked = self.run("rev-parse", "-q", "--verify", f"{ref}^3", check=False).strip()
        if untracked:
            out = self.run("diff-tree", "--root", "--no-commit-id", "-r", "--name-status", "-z", untracked,
                           check=False)
            files += [FileChange(f.path, "?", " ") for f in self._parse_name_status(out)]
        return files

    def stash_file_diff(self, ref: str, fc: FileChange, context: int = 3, ignore_ws: bool = False) -> bytes:
        if fc.untracked:
            return self.run_bytes("diff", *self._diff_opts(context, ignore_ws), EMPTY_TREE, f"{ref}^3",
                                  "--", fc.path, check=False)
        return self.run_bytes("diff", *self._diff_opts(context, ignore_ws), "-M", f"{ref}^1", ref,
                              "--", fc.path, check=False)

    def file_at(self, rev: str, path: str) -> bytes:
        return self.run_bytes("show", f"{rev}:{path}", check=False)

    # ------------------------------------------------------------------ file explorer / version compare
    WORKTREE = ""  # pseudo revision meaning "files on disk"

    def list_files(self, rev: str = "") -> list[str]:
        """All files at a revision; rev == "" lists the working tree (tracked + untracked, not ignored)."""
        if rev:
            out = self.run("ls-tree", "-r", "-z", "--name-only", "--full-tree", rev, check=False)
        else:
            out = self.run("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--deduplicate",
                           check=False)
        return sorted({p for p in out.split("\0") if p})

    def read_file(self, rev: str, path: str, limit: int = 8 * 1024 * 1024) -> bytes:
        if not rev:
            try:
                with open(os.path.join(self.path, path), "rb") as f:
                    return f.read(limit)
            except OSError:
                return b""
        return self.file_at(rev, path)[:limit]

    def file_revisions(self, path: str, max_count: int = 300) -> list[Commit]:
        return self.log(path=path, max_count=max_count)

    def diff_versions(self, rev_a: str, path_a: str, rev_b: str, path_b: str, context: int = 3,
                      ignore_ws: bool = False) -> bytes:
        """Diff file `path_a@rev_a` against `path_b@rev_b`; empty rev means the working tree file.
        Paths may differ (renames, or comparing two different files)."""
        opts = self._diff_opts(context, ignore_ws)
        if rev_a and rev_b:
            return self.run_bytes("diff", *opts, f"{rev_a}:{path_a}", f"{rev_b}:{path_b}", check=False)
        if not rev_a and not rev_b:
            return self.diff_paths(os.path.join(self.path, path_a), os.path.join(self.path, path_b), context,
                                   ignore_ws)
        if rev_a and path_a == path_b:  # revision vs worktree for the same path: native, keeps rename-free headers
            return self.run_bytes("diff", *opts, rev_a, "--", path_a, check=False)
        # different paths across rev/worktree: materialise the blob into a temp file
        blob_rev, blob_path, disk = (rev_a, path_a, path_b) if rev_a else (rev_b, path_b, path_a)
        fd, tmp = tempfile.mkstemp(prefix="gitcat-", suffix=os.path.splitext(blob_path)[1])
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(self.file_at(blob_rev, blob_path))
            left, right = (tmp, os.path.join(self.path, disk)) if rev_a else (os.path.join(self.path, disk), tmp)
            return self.diff_paths(left, right, context, ignore_ws)
        finally:
            os.unlink(tmp)

    def diff_paths(self, a: str, b: str, context: int = 3, ignore_ws: bool = False) -> bytes:
        """`git diff --no-index` of two arbitrary files or folders (may be outside the repository)."""
        code, out, err = run_git(["diff", "--no-index", *self._diff_opts(context, ignore_ws), "--", a, b], self.path)
        if code not in (0, 1):
            raise GitError(["diff", "--no-index"], code, decode(out), decode(err))
        return out

    def diff_trees(self, a: str, b: str, context: int = 3, ignore_ws: bool = False) -> bytes:
        """Whole-tree diff; empty b compares a with the working tree."""
        return self.run_bytes("diff", *self._diff_opts(context, ignore_ws), "-M", a, *([b] if b else []), check=False)

    def grep(self, pattern: str, rev: str = "", ignore_case: bool = True, regex: bool = False,
             max_count: int = 2000) -> list[tuple[str, int, str]]:
        """Search file contents; returns (path, line, text)."""
        args = ["grep", "-n", "-I", "--no-color", "--full-name"]
        args += ["-i"] if ignore_case else []
        args += ["-E"] if regex else ["-F"]
        args += ["--untracked"] if not rev else []
        args += ["-e", pattern] + ([rev] if rev else [])
        res = []
        for line in self.run(*args, check=False).splitlines()[:max_count]:
            if rev and line.startswith(rev + ":"):
                line = line[len(rev) + 1:]
            parts = line.split(":", 2)
            if len(parts) == 3 and parts[1].isdigit():
                res.append((parts[0], int(parts[1]), parts[2]))
        return res

    def all_refs_for_picker(self) -> list[str]:
        out = self.run("for-each-ref", "--format=%(refname:short)", "--sort=-committerdate", "refs/heads",
                       "refs/remotes", "refs/tags", check=False)
        return [r for r in out.splitlines() if r and not r.endswith("/HEAD")]

    def last_message(self) -> str:
        return self.run("log", "-1", "--format=%B", check=False).strip()

    def recent_messages(self, n: int = 15) -> list[str]:
        if not self.has_commits():
            return []
        return [s for s in self.run("log", f"-{n}", "--format=%s", "--no-merges").splitlines() if s]

    def blame(self, path: str, rev: str = "") -> list[tuple[str, str, str, int, str]]:
        """Return [(sha, author, date, line_no, text)]."""
        args = ["blame", "--porcelain", "-w"]
        if rev:
            args.append(rev)
        out = self.run(*args, "--", path)
        res = []
        meta: dict[str, tuple[str, str]] = {}
        sha, ln = "", 0
        author, ts = "", ""
        for line in out.splitlines():
            if line.startswith("\t"):
                if sha not in meta:
                    meta[sha] = (author, ts)
                a, d = meta[sha]
                res.append((sha, a, d, ln, line[1:]))
            else:
                parts = line.split(" ")
                if len(parts[0]) == 40 and all(c in "0123456789abcdef" for c in parts[0]) and len(parts) >= 3:
                    sha, ln = parts[0], int(parts[2])
                elif line.startswith("author "):
                    author = line[7:]
                elif line.startswith("author-time "):
                    ts = _dt.datetime.fromtimestamp(int(line[12:])).strftime("%Y-%m-%d")
        return res

    def reflog(self, n: int = 500) -> list[tuple[str, str, str, str]]:
        out = self.run("reflog", f"-n{n}", "--format=%H%x1f%gd%x1f%gs%x1f%cr", check=False)
        return [tuple(ln.split("\x1f")) for ln in out.splitlines() if ln.count("\x1f") == 3]  # type: ignore

    def tags_by_version(self) -> list[str]:
        tags = [t for t in self.run("tag", "--list", check=False).splitlines() if t]
        return sorted(tags, key=semver_key, reverse=True)

    def latest_version_tag(self) -> str:
        for t in self.tags_by_version():
            if SEMVER_RE.match(t):
                return t
        return ""

    def log_since(self, tag: str, max_count: int = 200) -> list[str]:
        rng = f"{tag}..HEAD" if tag else "HEAD"
        return [s for s in self.run("log", f"--max-count={max_count}", "--no-merges", "--format=%s", rng,
                                    check=False).splitlines() if s]

    def get_config(self, key: str, global_: bool = False) -> str:
        return self.run("config", *(["--global"] if global_ else []), "--get", key, check=False).strip()

    def set_config(self, key: str, value: str, global_: bool = False) -> str:
        if not value:
            return self.do("config", *(["--global"] if global_ else []), "--unset", key) \
                if self.get_config(key, global_) else ""
        return self.do("config", *(["--global"] if global_ else []), key, value)

    def stats(self) -> dict:
        """Lightweight repository statistics for the dashboard."""
        res = {"commits": 0, "authors": [], "branches": 0, "tags": 0}
        if not self.has_commits():
            return res
        res["commits"] = int(self.run("rev-list", "--count", "HEAD", check=False).strip() or 0)
        out = self.run("shortlog", "-sne", "HEAD", check=False)
        authors = []
        for line in out.splitlines():
            line = line.strip()
            if "\t" in line:
                n, who = line.split("\t", 1)
                authors.append((int(n), who))
        res["authors"] = authors[:10]
        return res

    # ------------------------------------------------------------------ working tree
    def _pathspec(self, cmd: list[str], paths: Iterable[str]) -> str:
        return self.do(*cmd, "--pathspec-from-file=-", "--pathspec-file-nul", input="\0".join(paths))

    def stage(self, paths: list[str]) -> str:
        return self._pathspec(["add", "-A"], paths)

    def stage_all(self) -> str:
        return self.do("add", "-A")

    def unstage(self, paths: list[str]) -> str:
        if self.has_commits():
            return self._pathspec(["restore", "--staged"], paths)
        return self._pathspec(["rm", "--cached", "-r", "-q"], paths)

    def unstage_all(self) -> str:
        if self.has_commits():
            return self.do("reset", "-q", "HEAD")
        return self.do("rm", "--cached", "-r", "-q", ".")

    def discard(self, changes: list[FileChange]) -> str:
        out = []
        tracked = [c.path for c in changes if not c.untracked]
        untracked = [c.path for c in changes if c.untracked]
        if tracked:
            out.append(self._pathspec(["restore", "--worktree"], tracked))
        if untracked:
            out.append(self.do("clean", "-f", "-q", "--", *untracked))
        return "\n".join(out)

    def clean_preview(self, dirs: bool = True, ignored: bool = False) -> list[str]:
        args = ["clean", "-n"] + (["-d"] if dirs else []) + (["-x"] if ignored else [])
        return [ln[13:] for ln in self.run(*args, check=False).splitlines() if ln.startswith("Would remove ")]

    def clean(self, dirs: bool = True, ignored: bool = False) -> str:
        return self.do("clean", "-f", *(["-d"] if dirs else []), *(["-x"] if ignored else []))

    def apply_patch(self, patch: bytes, cached: bool, reverse: bool) -> str:
        args = ["apply", "--recount", "--whitespace=nowarn"]
        if cached:
            args.append("--cached")
        if reverse:
            args.append("-R")
        args.append("-")
        code, out, err = run_git(args, self.path, patch)
        if self.logger:
            self.logger("git " + " ".join(args), code, decode(out), decode(err))
        if code != 0:
            raise GitError(args, code, decode(out), decode(err))
        return decode(out)

    def commit(self, msg: str, amend: bool = False, signoff: bool = False, no_verify: bool = False,
               allow_empty: bool = False) -> str:
        args = ["commit", "-F", "-"]
        if amend:
            args.append("--amend")
        if signoff:
            args.append("-s")
        if no_verify:
            args.append("--no-verify")
        if allow_empty:
            args.append("--allow-empty")
        return self.do(*args, input=msg)

    def checkout_side(self, path: str, side: str) -> str:
        out = self.do("checkout", f"--{side}", "--", path)
        return out + "\n" + self.do("add", "--", path)

    def mark_resolved(self, paths: list[str]) -> str:
        return self.do("add", "--", *paths)

    def restore_from(self, rev: str, path: str) -> str:
        return self.do("checkout", rev, "--", path)

    def add_to_gitignore(self, pattern: str) -> None:
        p = os.path.join(self.path, ".gitignore")
        prefix = ""
        if os.path.exists(p):
            with open(p, "rb") as f:
                data = f.read()
            if data and not data.endswith(b"\n"):
                prefix = "\n"
        with open(p, "a", encoding="utf-8", newline="\n") as f:
            f.write(prefix + pattern + "\n")

    # ------------------------------------------------------------------ branches / merging
    def checkout(self, ref: str) -> str:
        return self.do("checkout", ref)

    def checkout_tracking(self, remote_ref: str, local: str) -> str:
        return self.do("checkout", "-b", local, "--track", remote_ref)

    def create_branch(self, name: str, start: str = "", checkout: bool = True) -> str:
        if checkout:
            return self.do("checkout", "-b", name, *([start] if start else []))
        return self.do("branch", name, *([start] if start else []))

    def delete_branch(self, name: str, force: bool = False) -> str:
        return self.do("branch", "-D" if force else "-d", name)

    def rename_branch(self, old: str, new: str) -> str:
        return self.do("branch", "-m", old, new)

    def set_upstream(self, branch: str, upstream: str) -> str:
        return self.do("branch", f"--set-upstream-to={upstream}", branch)

    def merge(self, ref: str, no_ff: bool = False, ff_only: bool = False, squash: bool = False,
              no_commit: bool = False, message: str = "") -> str:
        args = ["merge"]
        if no_ff:
            args.append("--no-ff")
        if ff_only:
            args.append("--ff-only")
        if squash:
            args.append("--squash")
        if no_commit:
            args.append("--no-commit")
        args += ["-m", message] if message else ["--no-edit"]
        args.append(ref)
        return self.do(*args)

    def rebase(self, onto: str, autostash: bool = True) -> str:
        return self.do("rebase", *(["--autostash"] if autostash else []), onto)

    def cherry_pick(self, shas: list[str], mainline: bool = False, no_commit: bool = False) -> str:
        args = ["cherry-pick"]
        if mainline:
            args += ["-m", "1"]
        if no_commit:
            args.append("--no-commit")
        return self.do(*args, *shas)

    def revert(self, sha: str, mainline: bool = False) -> str:
        return self.do("revert", "--no-edit", *(["-m", "1"] if mainline else []), sha)

    def rebase_commits(self, base: str) -> list[Commit]:
        out = self.run("log", "--reverse", "--no-merges", f"--format={self.LOG_FMT}", f"{base}..HEAD")
        return self._parse_log(out)

    def rebase_interactive(self, base: str, plan: list[tuple[str, str, str]], workdir: str) -> str:
        """plan: [(action, sha, new_message)], action in pick/reword/squash/fixup/drop.
        A prepared todo file replaces git's sequence editor -> non-interactive interactive rebase."""
        lines = []
        for i, (action, sha, msg) in enumerate(plan):
            if action == "reword":
                mf = os.path.join(workdir, f"msg_{i}.txt")
                with open(mf, "w", encoding="utf-8", newline="\n") as f:
                    f.write(msg)
                lines.append(f"pick {sha}")
                lines.append(f'exec git commit --amend --no-verify -F "{mf.replace(os.sep, "/")}"')
            else:
                lines.append(f"{action} {sha}")
        todo = os.path.join(workdir, "todo.txt")
        with open(todo, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        editor = "cp '" + todo.replace(os.sep, "/") + "'"
        return self.do("rebase", "-i", "--autostash", base, env={"GIT_SEQUENCE_EDITOR": editor})

    def reset(self, target: str, mode: str = "mixed") -> str:
        return self.do("reset", f"--{mode}", target)

    def continue_op(self, st: RepoState) -> str:
        if st.rebasing:
            return self.do("rebase", "--continue")
        if st.cherry_picking:
            return self.do("cherry-pick", "--continue")
        if st.reverting:
            return self.do("revert", "--continue")
        if st.merging:
            return self.do("commit", "--no-edit")
        return ""

    def abort_op(self, st: RepoState) -> str:
        cmd = {"rebasing": "rebase", "merging": "merge", "cherry_picking": "cherry-pick",
               "reverting": "revert"}.get(st.kind)
        return self.do(cmd, "--abort") if cmd else ""

    def skip_op(self, st: RepoState) -> str:
        if st.rebasing:
            return self.do("rebase", "--skip")
        if st.cherry_picking:
            return self.do("cherry-pick", "--skip")
        return ""

    # ------------------------------------------------------------------ bisect
    def bisect_start(self, bad: str, good: str) -> str:
        return self.do("bisect", "start", bad, good)

    def bisect_mark(self, verdict: str) -> str:
        return self.do("bisect", verdict)

    def bisect_reset(self) -> str:
        return self.do("bisect", "reset")

    # ------------------------------------------------------------------ tags
    def create_tag(self, name: str, target: str = "HEAD", message: str = "", force: bool = False) -> str:
        args = ["tag"]
        if force:
            args.append("-f")
        if message:
            return self.do(*args, "-a", "-F", "-", name, target, input=message)
        return self.do(*args, name, target)

    def delete_tag(self, name: str) -> str:
        return self.do("tag", "-d", name)

    def push_tag(self, remote: str, name: str, force: bool = False) -> str:
        return self.do("push", *(["--force"] if force else []), remote, f"refs/tags/{name}")

    def delete_remote_tag(self, remote: str, name: str) -> str:
        return self.do("push", remote, "--delete", f"refs/tags/{name}")

    # ------------------------------------------------------------------ remotes
    def fetch(self, remote: str = "", prune: bool = True, progress: Optional[Progress] = None) -> str:
        # Never combine --prune with --tags: since git 2.17 that deletes every local tag missing on the remote.
        # Plain --prune only removes stale remote-tracking branches; tags on fetched history are auto-followed.
        args = ["fetch", "--progress"]
        if prune:
            args.append("--prune")
        args += [remote] if remote else ["--all"]
        return self.do_stream(*args, progress=progress)

    def pull(self, remote: str, branch: str, rebase: bool = False, autostash: bool = True,
             progress: Optional[Progress] = None) -> str:
        args = ["pull", "--progress", "--rebase" if rebase else "--no-rebase"]
        if autostash:
            args.append("--autostash")
        args.append(remote)
        if branch:
            args.append(branch)
        return self.do_stream(*args, progress=progress)

    def push(self, remote: str, local: str, remote_branch: str = "", set_upstream: bool = False,
             force_with_lease: bool = False, tags: bool = False, no_verify: bool = False,
             progress: Optional[Progress] = None) -> str:
        args = ["push", "--progress"]
        if set_upstream:
            args.append("-u")
        if force_with_lease:
            args.append("--force-with-lease")
        if tags:
            args.append("--tags")
        if no_verify:
            args.append("--no-verify")
        args.append(remote)
        if local:
            args.append(f"{local}:{remote_branch or local}")
        return self.do_stream(*args, progress=progress)

    def push_refs(self, remote: str, refspecs: list[str], progress: Optional[Progress] = None) -> str:
        return self.do_stream("push", "--progress", remote, *refspecs, progress=progress)

    def delete_remote_branch(self, remote: str, branch: str) -> str:
        return self.do("push", remote, "--delete", branch)

    def add_remote(self, name: str, url: str) -> str:
        return self.do("remote", "add", name, url)

    def remove_remote(self, name: str) -> str:
        return self.do("remote", "remove", name)

    def set_remote_url(self, name: str, url: str) -> str:
        return self.do("remote", "set-url", name, url)

    # ------------------------------------------------------------------ stash
    def stash_push(self, message: str = "", untracked: bool = False, keep_index: bool = False,
                   staged_only: bool = False, paths: Optional[list[str]] = None) -> str:
        args = ["stash", "push"]
        if untracked:
            args.append("--include-untracked")
        if keep_index:
            args.append("--keep-index")
        if staged_only:
            args.append("--staged")
        if message:
            args += ["-m", message]
        if paths:
            args += ["--", *paths]
        return self.do(*args)

    def stash_apply(self, ref: str, pop: bool = False, index: bool = False) -> str:
        return self.do("stash", "pop" if pop else "apply", *(["--index"] if index else []), ref)

    def stash_drop(self, ref: str) -> str:
        return self.do("stash", "drop", ref)

    def stash_branch(self, name: str, ref: str) -> str:
        return self.do("stash", "branch", name, ref)

    # ------------------------------------------------------------------ worktree / submodule
    def add_worktree(self, path: str, branch: str, new_branch: bool) -> str:
        if new_branch:
            return self.do("worktree", "add", "-b", branch, path)
        return self.do("worktree", "add", path, branch)

    def remove_worktree(self, path: str, force: bool = False) -> str:
        return self.do("worktree", "remove", *(["--force"] if force else []), path)

    def prune_worktrees(self) -> str:
        return self.do("worktree", "prune")

    def submodule_update(self, init: bool = True, recursive: bool = True, remote: bool = False) -> str:
        args = ["submodule", "update"]
        if init:
            args.append("--init")
        if recursive:
            args.append("--recursive")
        if remote:
            args.append("--remote")
        return self.do(*args)

    def submodule_add(self, url: str, path: str) -> str:
        return self.do("submodule", "add", url, path)

    # ------------------------------------------------------------------ misc
    def format_patch(self, shas: list[str], outdir: str) -> str:
        if len(shas) == 1:
            return self.do("format-patch", "-1", shas[0], "-o", outdir)
        return self.do("format-patch", f"{shas[-1]}^..{shas[0]}", "-o", outdir)

    def apply_mailbox(self, files: list[str]) -> str:
        return self.do("am", "-3", *files)

    def archive(self, ref: str, out: str) -> str:
        fmt = "tar.gz" if out.endswith((".tar.gz", ".tgz")) else "zip"
        return self.do("archive", f"--format={fmt}", "-o", out, ref)

    def gc(self) -> str:
        return self.do("gc", "--prune=now")

    def mergetool(self, path: str) -> str:
        return self.do("mergetool", "--no-prompt", "--", path)

    def custom(self, cmdline: str) -> str:
        tokens = [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'" else t
                  for t in shlex.split(cmdline, posix=False)]
        if tokens and tokens[0].lower() in ("git", "git.exe"):
            tokens = tokens[1:]
        if not tokens:
            return ""
        return self.do(*tokens)
