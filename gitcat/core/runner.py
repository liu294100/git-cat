"""Low-level git process execution: environment, decoding, progress streaming."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from typing import Callable, Optional


CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


PROGRESS_RE = re.compile(r"([A-Za-z][A-Za-z ]+?):\s+(\d+)%")


Logger = Callable[[str, int, str, str], None]


Progress = Callable[[str, int], None]


def decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("gbk", errors="replace")


class GitError(Exception):
    def __init__(self, args: list[str], code: int, stdout: str, stderr: str):
        self.git_args = args
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        msg = "\n".join(s for s in (stderr.strip(), stdout.strip()) if s) or f"git exit code {code}"
        super().__init__(msg)


def git_env(extra_env: Optional[dict] = None) -> dict:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_EDITOR"] = "true"
    env["GIT_SEQUENCE_EDITOR"] = "true"
    env["GIT_MERGE_AUTOEDIT"] = "no"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env.setdefault("LC_ALL", "C.UTF-8")
    # PyInstaller onefile builds must not leak their private DLL search path into git.
    env.pop("PYINSTALLER_RESET_ENVIRONMENT", None)
    if extra_env:
        env.update(extra_env)
    return env


GIT_PREFIX = ["git", "-c", "core.quotepath=false", "-c", "color.ui=never", "-c", "i18n.logOutputEncoding=utf-8"]


def run_git(args: list[str], cwd: str, input_bytes: Optional[bytes] = None,
         extra_env: Optional[dict] = None) -> tuple[int, bytes, bytes]:
    p = subprocess.run(
        [*GIT_PREFIX, *args], cwd=cwd, input=input_bytes, capture_output=True, env=git_env(extra_env),
        stdin=None if input_bytes is not None else subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    return p.returncode, p.stdout, p.stderr


def run_git_stream(args: list[str], cwd: str, progress: Optional[Progress]) -> tuple[int, str, str]:
    """Run a long network command and report "Receiving objects: 45%" style progress."""
    p = subprocess.Popen(
        [*GIT_PREFIX, *args], cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=git_env(), creationflags=CREATE_NO_WINDOW,
    )
    err_lines: list[str] = []
    buf = b""
    assert p.stderr is not None and p.stdout is not None
    out_chunks: list[bytes] = []
    reader = threading.Thread(target=lambda: out_chunks.append(p.stdout.read()), daemon=True)  # type: ignore
    reader.start()
    while True:
        ch = p.stderr.read(1)
        if not ch:
            break
        if ch in (b"\r", b"\n"):
            line = decode(buf).strip()
            buf = b""
            if not line:
                continue
            m = PROGRESS_RE.search(line)
            if m and progress:
                progress(m.group(1).strip(), int(m.group(2)))
            # Intermediate "\r" progress updates are only reported, the final "\n" line is kept.
            if ch == b"\n" or not m:
                err_lines.append(line)
        else:
            buf += ch
    if buf.strip():
        err_lines.append(decode(buf).strip())
    code = p.wait()
    reader.join(5)
    out = decode(b"".join(out_chunks))
    return code, out, "\n".join(err_lines)
