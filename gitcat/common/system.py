"""Operating-system integration: open files, explorer, terminal, editor."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _popen(args, **kw):
    return subprocess.Popen(args, creationflags=0x08000000 if sys.platform == "win32" else 0, **kw)


def open_path(path: str):
    if not path:
        return
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def reveal_in_explorer(path: str):
    if sys.platform == "win32" and os.path.exists(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    elif sys.platform == "darwin" and os.path.exists(path):
        subprocess.Popen(["open", "-R", path])
    else:
        open_path(os.path.dirname(path) if os.path.isfile(path) else path)


def open_terminal(path: str):
    if sys.platform == "win32":
        if shutil.which("wt"):
            subprocess.Popen(["wt", "-d", path])
            return
        gitbash = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Git", "git-bash.exe")
        if os.path.exists(gitbash):
            subprocess.Popen([gitbash, f"--cd={path}"])
            return
        subprocess.Popen("start cmd", shell=True, cwd=path)  # noqa: S602,S607
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Terminal", path])
    else:
        for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
            if shutil.which(term):
                subprocess.Popen([term], cwd=path)
                return


def open_in_editor(path: str, editor: str = ""):
    """Open with the configured editor command, VS Code / Kiro if present, else the OS default."""
    for cmd in ([editor] if editor else []) + ["kiro", "code"]:
        exe = shutil.which(cmd)
        if exe:
            _popen([exe, path], shell=exe.lower().endswith((".cmd", ".bat")))
            return
    open_path(path)


def git_version() -> str:
    try:
        return subprocess.run(["git", "--version"], capture_output=True, text=True,
                              creationflags=0x08000000 if sys.platform == "win32" else 0).stdout.strip()
    except OSError:
        return ""
