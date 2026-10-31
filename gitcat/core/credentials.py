"""Thin wrapper over `git credential` so tokens live in the user's credential helper
(Git Credential Manager, macOS Keychain, libsecret...) instead of GitCat's config file."""
from __future__ import annotations

import os
import shutil
import sys
from typing import Optional

from .runner import decode, run_git

# Never let a helper pop up a GUI or terminal prompt from a background thread.
_NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_ASKPASS": "", "SSH_ASKPASS": ""}


def _home() -> str:
    return os.path.expanduser("~")


def _payload(host: str, username: str = "", password: str = "", protocol: str = "https") -> bytes:
    lines = [f"protocol={protocol}", f"host={host}"]
    if username:
        lines.append(f"username={username}")
    if password:
        lines.append(f"password={password}")
    return ("\n".join(lines) + "\n\n").encode("utf-8")


def helpers() -> list[str]:
    code, out, _ = run_git(["config", "--get-all", "credential.helper"], _home())
    return [ln.strip() for ln in decode(out).splitlines() if ln.strip()] if code == 0 else []


def recommended_helper() -> str:
    if sys.platform == "win32" or shutil.which("git-credential-manager") or shutil.which("git-credential-manager-core"):
        return "manager"
    if sys.platform == "darwin":
        return "osxkeychain"
    if shutil.which("git-credential-libsecret"):
        return "libsecret"
    return "cache --timeout=86400"


def enable_helper(helper: str) -> None:
    code, out, err = run_git(["config", "--global", "credential.helper", helper], _home())
    if code != 0:
        raise RuntimeError(decode(err) or decode(out))


def fill(host: str, username: str = "", protocol: str = "https") -> Optional[tuple[str, str]]:
    """Return (username, secret) from the configured helpers, or None. Never prompts."""
    code, out, _ = run_git(["credential", "fill"], _home(), _payload(host, username, protocol=protocol), _NO_PROMPT)
    if code != 0:
        return None
    vals = dict(ln.split("=", 1) for ln in decode(out).splitlines() if "=" in ln)
    secret = vals.get("password", "")
    return (vals.get("username", username), secret) if secret else None


def approve(host: str, username: str, secret: str, protocol: str = "https") -> None:
    code, out, err = run_git(["credential", "approve"], _home(), _payload(host, username, secret, protocol),
                             _NO_PROMPT)
    if code != 0:
        raise RuntimeError(decode(err) or decode(out) or "git credential approve failed")


def reject(host: str, username: str = "", protocol: str = "https") -> None:
    run_git(["credential", "reject"], _home(), _payload(host, username, protocol=protocol), _NO_PROMPT)


def has_manager() -> bool:
    return any("manager" in h for h in helpers())


def browser_login(host: str, username: str = "") -> tuple[str, str]:
    """Interactive sign-in through Git Credential Manager (opens its OAuth / browser window).
    Blocks until the user finishes; call from a worker thread."""
    env = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "always"}
    code, out, err = run_git(["credential", "fill"], _home(), _payload(host, username), env)
    vals = dict(ln.split("=", 1) for ln in decode(out).splitlines() if "=" in ln)
    if code != 0 or not vals.get("password"):
        raise RuntimeError(decode(err).strip() or "sign-in cancelled")
    approve(host, vals.get("username", username), vals["password"])
    return vals.get("username", username), vals["password"]
