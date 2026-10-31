"""Application entry point: `python -m gitcat [repo-path]`."""
from __future__ import annotations

import os
import sys
import threading


def main() -> int:
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    from . import APP_NAME, __version__
    from .common.config import load_config
    from .common.i18n import set_language
    from .common.resources import set_windows_app_id
    from .services import updater

    if "--version" in sys.argv:
        print(f"{APP_NAME} {__version__}")
        return 0
    # Must run before any window exists: Windows groups the taskbar button by this ID and shows our
    # icon instead of python.exe's when running from source.
    set_windows_app_id()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName("gitcat")  # Linux/Wayland taskbar icon matching
    from .ui.icons import app_icon
    app.setWindowIcon(app_icon())  # inherited by every window and dialog → title bar, taskbar, Alt+Tab, dock
    cfg = load_config()
    cfg["language"] = set_language(cfg.get("language", ""))

    from .ui import theme
    theme.apply_theme(app, cfg.get("theme", "neon"))
    from .ui.main_window import MainWindow
    win = MainWindow(cfg)
    geo = cfg.get("geometry")
    if geo:
        win.restoreGeometry(QByteArray.fromHex(geo.encode()))
    win.show()
    for arg in sys.argv[1:]:
        if not arg.startswith("-") and os.path.isdir(arg):
            win.open_repo(os.path.abspath(arg))
    threading.Thread(target=updater.cleanup_previous_install, daemon=True).start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
