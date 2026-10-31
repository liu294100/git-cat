"""Application icon: one multi-resolution QIcon shared by windows, dialogs, taskbar and dock."""
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtGui import QIcon

from ..common.resources import icon_files, icon_path

_ICON: Optional[QIcon] = None


def app_icon() -> QIcon:
    global _ICON
    if _ICON is None:
        icon = QIcon()
        if sys.platform == "win32" and icon_path("ico").is_file():
            icon.addFile(str(icon_path("ico")))  # all embedded ICO sizes
        for f in icon_files():
            icon.addFile(str(f))
        _ICON = icon
    return _ICON
