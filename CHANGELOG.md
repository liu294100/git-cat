# Changelog

## v1.0.0

First public release.

### Working copy
- Staged / unstaged file lists with filter; stage, unstage or discard whole files, single hunks or selected lines.
- Unified and side-by-side diff with line numbers and intraline (word-level) highlighting.
- Conflict resolution: use ours / theirs, open the merge tool, mark resolved; banner to continue, skip or abort a merge, rebase, cherry-pick or revert.
- Commit with amend, sign-off and skip-hooks; "commit and push"; recent message picker; undo last commit.

### History
- Commit graph with lanes, branch / tag / remote badges and author avatars.
- Quick filter plus deep search by message, author, code (`-S`) or file path.
- Commit details, changed files and per-file diffs; compare any two selected commits.
- Blame, file history, restore a file from any commit, save any version of a file, export patches and archives, reflog.

### Files and version compare
- Files page: browse the project at the working tree or any branch, tag or commit; code viewer with line numbers and find.
- Content search (`git grep`) across the working tree or a revision, with regex and case options.
- Compare any file at any revision with any other file or revision, the working tree, or a file outside the repository.

### Branches, tags and releases
- Checkout, tracking checkout, create, rename, delete (local and remote), set upstream, compare branches.
- Merge (fast-forward, no-ff, ff-only, squash), rebase, interactive rebase (pick / reword / squash / fixup / drop / reorder), cherry-pick, revert, reset (soft / mixed / hard), bisect.
- Annotated and lightweight tags; push and delete remote tags.
- Release wizard: detects version files (`__init__.py`, `package.json`, `pyproject.toml`, `Cargo.toml`, `setup.py`, `build.gradle`, `VERSION`…), bumps the semantic version, prepends `CHANGELOG.md`, commits, tags and pushes.

### Hosting providers and accounts
- GitHub / GitHub Enterprise, GitLab (cloud and self-managed), Gitee, Gitea / Forgejo / Codeberg, Bitbucket Cloud, Azure DevOps, and any other git host.
- Sign in with a personal access token, through the browser (Git Credential Manager), or with an SSH key; verify, edit, set default and sign out.
- Secrets are stored in git's credential helper (Credential Manager, Keychain, libsecret), so GitCat and the command line share one login. Plain-text storage is opt-in.
- Credentials are also picked up from the environment: `GITHUB_TOKEN` / `GITLAB_TOKEN` / …, the `gh` and `glab` CLIs, and existing git credentials.
- SSH key generation, public-key copy, opening the provider's key page and connection test.
- Bind an account to a repository: sets `user.name`, `user.email`, `core.sshCommand` and the remote URL user, for clean multi-account setups.
- Clone from "my repositories" on any configured account.
- Provider-aware links: create pull / merge request, open branch, commit, compare and CI pages.

### CI and releases dashboard
- GitHub Actions, GitLab pipelines, Bitbucket Pipelines and Gitea Actions runs with job and step status; auto-refresh while running.
- Re-run, re-run failed, cancel and trigger workflows / pipelines (GitHub, GitLab).
- Releases list for GitHub, GitLab, Gitea and Gitee; add a release workflow template (GitHub Actions, GitLab CI, Gitea).

### Command Center
- 80 git commands grouped by task, each with a form for its options, live command-line preview, link to the official docs, confirmation for destructive commands, and output pane.
- Free-form git command line with history.

### More
- Multiple repositories in tabs, stashes (including partial and untracked), worktrees, submodules, clean, apply patches, `.gitignore` helpers, git console, command palette (`Ctrl+Shift+P`), insights dashboard.
- Four themes and ten languages: 简体中文, English, 日本語, 한국어, Français, Español, Português, ไทย, Bahasa Melayu, Русский.
- Application icon at 16–1024 px for title bar, taskbar, Alt+Tab, Dock and Explorer; Windows file version information.
- All git work runs off the UI thread; refresh queries run in parallel and are coalesced; history reloads only when refs change; `.git` changes are watched instead of polled.
- Self-update from GitHub Releases with SHA-256 verification.
- Windows x64, macOS arm64 and macOS x64 packages built and published by GitHub Actions.
