"""Collect a full repository snapshot in a worker thread so the GUI never blocks on git."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

from ..core.models import Commit, FileChange, Ref, RepoState, Submodule, Worktree
from ..core.repo import Repo


@dataclass
class Snapshot:
    changes: list[FileChange]
    refs: list[Ref]
    remotes: dict[str, str]
    stashes: list[tuple[str, str, str]]
    submodules: list[Submodule]
    worktrees: list[Worktree]
    branch: str
    ahead: int
    behind: int
    state: RepoState
    head: str
    recent: list[str]
    signature: tuple
    commits: Optional[list[Commit]] = None  # None = history unchanged, keep current model
    account: str = ""  # gitcat.account bound to this repository
    errors: list[str] = field(default_factory=list)


_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="gitcat-snap")


def _ahead_behind(repo: Repo) -> tuple[int, int]:
    return repo.ahead_behind() if repo.current_branch() and repo.upstream() else (0, 0)


def load_snapshot(repo: Repo, all_refs: bool, log_limit: int, prev_signature: Optional[tuple],
                  force_log: bool) -> Snapshot:
    """Run the independent read-only git queries concurrently (process start-up dominates on Windows)."""
    jobs = {
        "refs": repo.refs, "head": repo.head_sha, "branch": repo.current_branch, "status": repo.status,
        "remotes": repo.remotes, "stashes": repo.stashes, "subs": repo.submodules, "wts": repo.worktrees,
        "state": repo.state, "recent": repo.recent_messages, "ab": lambda: _ahead_behind(repo),
        "account": lambda: repo.get_config("gitcat.account"),
    }
    # The log is the most expensive query: start it speculatively unless we know it is unchanged.
    log_future = _POOL.submit(repo.log, max_count=log_limit, all_refs=all_refs) if force_log or not prev_signature \
        else None
    futures = {k: _POOL.submit(fn) for k, fn in jobs.items()}
    res = {k: f.result() for k, f in futures.items()}
    signature = (res["head"], tuple((r.full, r.sha) for r in res["refs"]), all_refs, log_limit)
    commits = None
    if log_future is not None:
        commits = log_future.result()
    elif signature != prev_signature:
        commits = repo.log(all_refs=all_refs, max_count=log_limit)
    ahead, behind = res["ab"]
    return Snapshot(
        changes=res["status"], refs=res["refs"], remotes=res["remotes"], stashes=res["stashes"],
        submodules=res["subs"], worktrees=res["wts"], branch=res["branch"] or "", ahead=ahead, behind=behind,
        state=res["state"], head=res["head"], recent=res["recent"], signature=signature, commits=commits,
        account=res["account"],
    )
