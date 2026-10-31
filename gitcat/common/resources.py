from __future__ import annotations

import ctypes
import platform
import sys
from pathlib import Path

APP_USER_MODEL_ID = "GitCat.Client"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256, 512, 1024)


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parents[2]  # project root (gitcat/common/resources.py)
    return base / relative_path


def icon_path(kind: str = "png") -> Path:
    names = {"png": "assets/gitcat.png", "small": "assets/gitcat-64.png",
             "ico": "assets/gitcat.ico", "icns": "assets/gitcat.icns"}
    return resource_path(names[kind])


def icon_files() -> list[Path]:
    """Every icon bitmap that exists, smallest first (for a multi-resolution QIcon)."""
    files = [resource_path(f"assets/icons/gitcat-{s}.png") for s in ICON_SIZES]
    files = [f for f in files if f.is_file()]
    return files or [icon_path("png")]


def set_windows_app_id() -> None:
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
