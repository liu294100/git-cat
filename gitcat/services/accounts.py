"""Hosting accounts: storage, token resolution from the environment, SSH keys and per-repo binding.

Secrets are written to git's own credential helper (Git Credential Manager / Keychain / libsecret).
GitCat's config only keeps non-secret metadata, unless the user explicitly chooses config storage.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

from ..core import credentials
from ..core.hosting import DEFAULT_HOSTS, RemoteInfo, guess_provider, parse_remote
from ..core.repo import Repo
from ..core.runner import CREATE_NO_WINDOW, decode, run_git

AUTH_TOKEN, AUTH_SSH, AUTH_BROWSER = "token", "ssh", "browser"
STORE_HELPER, STORE_CONFIG = "helper", "config"

ENV_TOKENS = {
    "github": ["GITHUB_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN"],
    "gitlab": ["GITLAB_TOKEN", "GL_TOKEN", "GITLAB_PRIVATE_TOKEN"],
    "gitee": ["GITEE_TOKEN"],
    "gitea": ["GITEA_TOKEN", "FORGEJO_TOKEN"],
    "bitbucket": ["BITBUCKET_TOKEN"],
    "azure": ["AZURE_DEVOPS_EXT_PAT", "SYSTEM_ACCESSTOKEN"],
}


@dataclass
class Account:
    provider: str
    host: str
    username: str = ""
    name: str = ""
    email: str = ""
    avatar: str = ""
    auth: str = AUTH_TOKEN
    storage: str = STORE_HELPER
    ssh_key: str = ""
    default: bool = False
    token: str = ""  # only persisted when storage == "config"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def label(self) -> str:
        who = self.username or self.name or "?"
        return f"{who} @ {self.host}"

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.storage != STORE_CONFIG:
            d.pop("token", None)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Account":
        keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in keys})


def _quiet(args: list[str], timeout: int = 8, cwd: Optional[str] = None) -> tuple[int, str]:
    exe = shutil.which(args[0])
    if not exe:
        return 127, ""
    try:
        p = subprocess.run([exe, *args[1:]], capture_output=True, timeout=timeout, cwd=cwd,
                           stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        return p.returncode, decode(p.stdout + p.stderr)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


class AccountStore:
    """Accounts persisted inside the app config dict under "accounts"."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    # ---------------------------------------------------------------- persistence
    def all(self) -> list[Account]:
        return [Account.from_dict(d) for d in self.cfg.get("accounts", []) if isinstance(d, dict)]

    def _write(self, accounts: list[Account]) -> None:
        self.cfg["accounts"] = [a.to_dict() for a in accounts]

    def get(self, account_id: str) -> Optional[Account]:
        return next((a for a in self.all() if a.id == account_id), None)

    def save(self, acc: Account, secret: str = "") -> None:
        """Insert or update an account; store the secret according to acc.storage."""
        if secret and acc.auth == AUTH_TOKEN:
            if acc.storage == STORE_HELPER:
                credentials.approve(acc.host, acc.username or "oauth2", secret)
                acc.token = ""
            else:
                acc.token = secret
        accounts = [a for a in self.all() if a.id != acc.id]
        if acc.default or not any(a.host == acc.host for a in accounts):
            for a in accounts:
                if a.host == acc.host:
                    a.default = False
            acc.default = True
        accounts.append(acc)
        accounts.sort(key=lambda a: (a.provider, a.host, a.username))
        self._write(accounts)

    def set_default(self, account_id: str) -> None:
        accounts = self.all()
        target = next((a for a in accounts if a.id == account_id), None)
        if not target:
            return
        for a in accounts:
            if a.host == target.host:
                a.default = a.id == account_id
        self._write(accounts)

    def logout(self, account_id: str) -> None:
        acc = self.get(account_id)
        if not acc:
            return
        if acc.auth in (AUTH_TOKEN, AUTH_BROWSER):
            credentials.reject(acc.host, acc.username)
        rest = [a for a in self.all() if a.id != account_id]
        if acc.default:
            nxt = next((a for a in rest if a.host == acc.host), None)
            if nxt:
                nxt.default = True
        self._write(rest)

    # ---------------------------------------------------------------- lookup
    def known_hosts(self) -> dict[str, str]:
        """host -> provider for configured (possibly self-hosted) accounts."""
        return {a.host: a.provider for a in self.all()}

    def parse(self, url: str) -> Optional[RemoteInfo]:
        return parse_remote(url, self.known_hosts())

    def for_host(self, host: str, username: str = "") -> Optional[Account]:
        cands = [a for a in self.all() if a.host == host.lower()]
        if username:
            exact = [a for a in cands if a.username == username]
            if exact:
                return exact[0]
        return next((a for a in cands if a.default), cands[0] if cands else None)

    def for_repo(self, repo: Repo) -> tuple[Optional[RemoteInfo], Optional[Account]]:
        remotes = repo.remotes()
        url = remotes.get("origin") or next(iter(remotes.values()), "")
        info = self.parse(url) if url else None
        if not info:
            return None, None
        bound = repo.get_config("gitcat.account")
        acc = self.get(bound) if bound else None
        return info, acc or self.for_host(info.host, info.user if info.scheme != "ssh" else "")

    def token_for(self, provider: str, host: str, username: str = "") -> tuple[str, str, str]:
        """Resolve (token, username, source). Order: account → env vars → provider CLI → git credential helper."""
        acc = self.for_host(host, username)
        if acc:
            if acc.storage == STORE_CONFIG and acc.token:
                return acc.token, acc.username, "account"
            if acc.auth in (AUTH_TOKEN, AUTH_BROWSER):
                got = credentials.fill(host, acc.username)
                if got:
                    return got[1], got[0], "account"
            username = username or acc.username
        for var in ENV_TOKENS.get(provider, []):
            if os.environ.get(var):
                return os.environ[var], username, f"env:{var}"
        cli = cli_token(provider, host)
        if cli:
            return cli, username, f"cli:{'gh' if provider == 'github' else 'glab'}"
        got = credentials.fill(host, username)
        if got:
            return got[1], got[0], "git-credential"
        return "", username, ""


def cli_token(provider: str, host: str) -> str:
    if provider == "github":
        code, out = _quiet(["gh", "auth", "token", "--hostname", host], 5)
        return out.strip().splitlines()[-1] if code == 0 and out.strip() else ""
    if provider == "gitlab":
        code, out = _quiet(["glab", "config", "get", "token", "--host", host], 5)
        return out.strip() if code == 0 and out.strip() and " " not in out.strip() else ""
    return ""


# ==================================================================== environment detection
@dataclass
class Environment:
    git_version: str = ""
    user_name: str = ""
    user_email: str = ""
    helpers: list[str] = field(default_factory=list)
    ssh_keys: list[str] = field(default_factory=list)
    env_tokens: list[tuple[str, str]] = field(default_factory=list)   # (provider, VAR)
    cli_logins: list[tuple[str, str]] = field(default_factory=list)   # (provider, host)
    ssh_agent: bool = False


def detect_environment() -> Environment:
    home = os.path.expanduser("~")
    env = Environment()
    code, out, _ = run_git(["--version"], home)
    env.git_version = decode(out).strip() if code == 0 else ""
    for key, attr in (("user.name", "user_name"), ("user.email", "user_email")):
        code, out, _ = run_git(["config", "--global", "--get", key], home)
        setattr(env, attr, decode(out).strip() if code == 0 else "")
    env.helpers = credentials.helpers()
    env.ssh_keys = list_ssh_keys()
    env.env_tokens = [(p, v) for p, vs in ENV_TOKENS.items() for v in vs if os.environ.get(v)]
    env.ssh_agent = bool(os.environ.get("SSH_AUTH_SOCK")) or sys.platform == "win32"
    code, out = _quiet(["gh", "auth", "status"], 6)
    if code == 0 or "Logged in" in out:
        for line in out.splitlines():
            line = line.strip()
            if line and not line.startswith(("-", "✓", "X", "!")) and "." in line and " " not in line:
                env.cli_logins.append(("github", line))
        if not env.cli_logins and "Logged in" in out:
            env.cli_logins.append(("github", "github.com"))
    code, out = _quiet(["glab", "auth", "status"], 6)
    if "Logged in" in out:
        for line in out.splitlines():
            line = line.strip()
            if line and "." in line and " " not in line:
                env.cli_logins.append(("gitlab", line))
    return env


def import_cli(provider: str, host: str) -> str:
    return cli_token(provider, host)


# ==================================================================== SSH
def ssh_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".ssh")


def list_ssh_keys() -> list[str]:
    d = ssh_dir()
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f[:-4]) for f in os.listdir(d)
                  if f.endswith(".pub") and os.path.exists(os.path.join(d, f[:-4])))


def public_key(path: str) -> str:
    try:
        with open(path + ".pub", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def generate_ssh_key(email: str, name: str = "id_ed25519") -> str:
    os.makedirs(ssh_dir(), exist_ok=True)
    path = os.path.join(ssh_dir(), name)
    if os.path.exists(path):
        raise FileExistsError(path)
    code, out = _quiet(["ssh-keygen", "-t", "ed25519", "-C", email or "gitcat", "-f", path, "-N", ""], 30)
    if code != 0 or not os.path.exists(path):
        raise RuntimeError(out or "ssh-keygen failed (is OpenSSH installed?)")
    return path


def ssh_command(key: str) -> str:
    return f'ssh -i "{key.replace(os.sep, "/")}" -o IdentitiesOnly=yes'


def test_ssh(host: str, key: str = "") -> tuple[bool, str]:
    args = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10"]
    if key:
        args += ["-i", key, "-o", "IdentitiesOnly=yes"]
    user = "git"
    if host.endswith("dev.azure.com"):
        host = "ssh.dev.azure.com"
    args.append(f"{user}@{host}")
    code, out = _quiet(args, 20)
    low = out.lower()
    ok = any(s in low for s in ("successfully authenticated", "welcome to gitlab", "authenticated via",
                                "you've successfully", "hi ", "logged in as", "shell access is not supported",
                                "authenticated", "does not provide shell access"))
    return ok and "permission denied" not in low, out.strip()


# ==================================================================== bind account to a repository
def apply_to_repo(repo: Repo, acc: Account, set_identity: bool = True) -> list[str]:
    """Make this repo use the account: identity, SSH key and a username-qualified HTTPS remote."""
    done = []
    repo.set_config("gitcat.account", acc.id)
    if set_identity:
        if acc.name:
            repo.set_config("user.name", acc.name)
            done.append(f"user.name = {acc.name}")
        if acc.email:
            repo.set_config("user.email", acc.email)
            done.append(f"user.email = {acc.email}")
    if acc.auth == AUTH_SSH and acc.ssh_key:
        repo.set_config("core.sshCommand", ssh_command(acc.ssh_key))
        done.append("core.sshCommand → " + os.path.basename(acc.ssh_key))
    for name, url in repo.remotes().items():
        info = parse_remote(url, {acc.host: acc.provider})
        if not info or info.host != acc.host:
            continue
        if acc.auth == AUTH_SSH:
            new = f"git@{info.host}:{info.path}.git"
        elif acc.username and info.scheme == "https":
            new = f"https://{acc.username}@{info.host}/{info.path}.git"
        else:
            continue
        if new != url:
            repo.set_remote_url(name, new)
            done.append(f"{name} → {new}")
    return done


def default_host(provider: str) -> str:
    return DEFAULT_HOSTS.get(provider, "")


__all__ = ["Account", "AccountStore", "Environment", "detect_environment", "list_ssh_keys", "public_key",
           "generate_ssh_key", "test_ssh", "apply_to_repo", "default_host", "guess_provider", "import_cli",
           "AUTH_TOKEN", "AUTH_SSH", "AUTH_BROWSER", "STORE_HELPER", "STORE_CONFIG"]
