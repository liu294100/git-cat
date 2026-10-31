"""Themes: a palette dict per theme rendered into one Qt style sheet template."""
from __future__ import annotations

from string import Template

from PySide6.QtGui import QColor, QPalette

THEMES: dict[str, dict[str, str]] = {
    "neon": {
        "bg": "#0f1220", "panel": "#151a2e", "panel2": "#1b2140", "input": "#0b0e1a", "border": "#262d52",
        "text": "#dfe5ff", "muted": "#8a93c0", "accent": "#8b5cf6", "accent2": "#22d3ee",
        "hover": "#222a50", "sel": "#3b2f7a", "danger": "#ff5c8a", "ok": "#34d399", "warn": "#fbbf24",
        "add_bg": "#0f3326", "del_bg": "#3d1424", "hunk_bg": "#1a2150", "add_fg": "#a7f3d0",
        "del_fg": "#fecdd3", "hunk_fg": "#a5b4fc", "head_fg": "#c4b5fd", "gutter": "#0d1020",
    },
    "aurora": {
        "bg": "#0c1716", "panel": "#112220", "panel2": "#16302c", "input": "#08110f", "border": "#1f423c",
        "text": "#dcf5ef", "muted": "#7fa8a0", "accent": "#10b981", "accent2": "#38bdf8",
        "hover": "#1a3a35", "sel": "#11524a", "danger": "#fb7185", "ok": "#4ade80", "warn": "#facc15",
        "add_bg": "#0e3a28", "del_bg": "#3a1620", "hunk_bg": "#123040", "add_fg": "#bbf7d0",
        "del_fg": "#fecdd3", "hunk_fg": "#7dd3fc", "head_fg": "#99f6e4", "gutter": "#0a1413",
    },
    "sunset": {
        "bg": "#1a1014", "panel": "#22151b", "panel2": "#2e1b24", "input": "#120b0e", "border": "#4a2734",
        "text": "#ffe9ef", "muted": "#c0909f", "accent": "#f43f5e", "accent2": "#fb923c",
        "hover": "#3a2230", "sel": "#5c2238", "danger": "#ff6b6b", "ok": "#4ade80", "warn": "#fcd34d",
        "add_bg": "#13341f", "del_bg": "#47141f", "hunk_bg": "#3a1d2a", "add_fg": "#bbf7d0",
        "del_fg": "#fecdd3", "hunk_fg": "#fdba74", "head_fg": "#fda4af", "gutter": "#140c10",
    },
    "light": {
        "bg": "#f4f6fb", "panel": "#ffffff", "panel2": "#eef1f8", "input": "#ffffff", "border": "#d6dbe8",
        "text": "#1f2437", "muted": "#6b7390", "accent": "#6d28d9", "accent2": "#0891b2",
        "hover": "#e6e9f5", "sel": "#d9d0fb", "danger": "#e11d48", "ok": "#059669", "warn": "#d97706",
        "add_bg": "#dcfce7", "del_bg": "#ffe4e6", "hunk_bg": "#e0e7ff", "add_fg": "#14532d",
        "del_fg": "#881337", "hunk_fg": "#3730a3", "head_fg": "#5b21b6", "gutter": "#eef1f8",
    },
}

C: dict[str, str] = dict(THEMES["neon"])
CURRENT = "neon"

STYLE = Template("""
* { font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", "Noto Sans", "Leelawadee UI",
    "Malgun Gothic", "Yu Gothic UI", sans-serif; font-size: 13px; }
QWidget { background: transparent; color: $text; }
QMainWindow, QDialog, QMessageBox, QInputDialog, QFileDialog { background: $bg; }

QWidget#root, QStackedWidget, QSplitter, QScrollArea > QWidget > QWidget { background: $bg; }
QFrame#card, QWidget#card { background: $panel; border: 1px solid $border; border-radius: 12px; }
QFrame#header { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $panel, stop:0.6 $panel2, stop:1 $panel);
    border-bottom: 1px solid $border; }
QLabel#brand { font-size: 17px; font-weight: 800; color: $text; }
QLabel#brandAccent { font-size: 17px; font-weight: 800; color: $accent2; }
QLabel#hero { font-size: 38px; font-weight: 800; color: $text; }
QLabel#heroSub { font-size: 15px; color: $muted; }
QLabel#section { color: $muted; font-weight: 700; font-size: 12px; letter-spacing: 1px; }
QLabel#muted { color: $muted; }
QLabel#diffTitle { color: $text; font-weight: 700; }
QLabel#error { color: $danger; }
QLabel#pill { background: $panel2; border: 1px solid $border; border-radius: 10px; padding: 3px 10px; color: $text; }
QLabel#pillAccent { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $accent, stop:1 $accent2);
    border-radius: 10px; padding: 3px 10px; color: white; font-weight: 700; }
QLabel#stat { font-size: 26px; font-weight: 800; color: $accent2; }
QToolButton { padding: 6px 10px; border-radius: 8px; color: $text; border: 1px solid transparent; }
QToolButton:hover { background: $hover; border-color: $border; }
QToolButton:pressed { background: $sel; }
QToolButton:checked { background: $sel; border-color: $accent; }
QToolButton:disabled { color: $muted; }
QToolButton#nav { padding: 8px 16px; border-radius: 10px; font-weight: 600; color: $muted; }
QToolButton#nav:checked { color: white; border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $accent, stop:1 $accent2); }
QToolButton#nav:hover:!checked { color: $text; background: $hover; }
QToolButton::menu-indicator { image: none; width: 0; }
QMenuBar { background: $panel; border-bottom: 1px solid $border; }
QMenuBar::item { padding: 5px 10px; border-radius: 6px; }
QMenuBar::item:selected { background: $hover; }
QMenu { background: $panel; border: 1px solid $border; padding: 6px; border-radius: 10px; }
QMenu::item { padding: 7px 26px 7px 18px; border-radius: 6px; }
QMenu::item:selected { background: $sel; color: white; }
QMenu::item:disabled { color: $muted; }
QMenu::separator { height: 1px; background: $border; margin: 5px 8px; }
QTreeWidget, QTreeView, QListWidget, QTableView, QTableWidget, QPlainTextEdit, QTextBrowser, QTextEdit,
QLineEdit, QComboBox, QSpinBox {
  background: $input; border: 1px solid $border; border-radius: 8px; color: $text;
  selection-background-color: $sel; selection-color: white; }
QLineEdit, QComboBox, QSpinBox { padding: 6px 10px; min-height: 18px; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus { border: 1px solid $accent; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: $panel; border: 1px solid $border; selection-background-color: $sel; }
QTreeWidget::item, QListWidget::item { padding: 5px 4px; border-radius: 6px; }
QTreeWidget::item:hover, QListWidget::item:hover, QTableView::item:hover { background: $hover; }
QTreeWidget::item:selected, QListWidget::item:selected { background: $sel; color: white; }
QTableView { gridline-color: transparent; alternate-background-color: $panel; }
QTableView::item { padding: 2px 4px; border: none; }
QTableView::item:selected { background: $sel; color: white; }
QHeaderView { background: $panel; border: none; }
QHeaderView::section { background: $panel; color: $muted; border: none; border-bottom: 1px solid $border;
  padding: 6px 8px; font-weight: 600; }
QPushButton { background: $panel2; border: 1px solid $border; border-radius: 8px; padding: 7px 14px; color: $text;
  font-weight: 600; }
QPushButton:hover { background: $hover; border-color: $accent; }
QPushButton:pressed { background: $sel; }
QPushButton:disabled { color: $muted; background: $panel; border-color: $border; }
QPushButton#primary { border: none; color: white; font-weight: 700;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $accent, stop:1 $accent2); }
QPushButton#primary:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $accent2, stop:1 $accent); }
QPushButton#primary:disabled { background: $panel2; color: $muted; }
QPushButton#danger { color: $danger; }
QPushButton#danger:hover { border-color: $danger; }
QPushButton#tile { text-align: left; padding: 14px 16px; border-radius: 12px; background: $panel; font-size: 14px; }
QPushButton#tile:hover { border-color: $accent2; background: $panel2; }
QFrame#banner { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5b3a0a, stop:1 #3a2a0a);
  border: 1px solid $warn; border-radius: 10px; }
QFrame#banner QLabel { color: #ffe7a8; font-weight: 700; }
QTabWidget::pane { border: none; }
QTabBar { background: transparent; }
QTabBar::tab { background: transparent; padding: 8px 16px; border: none; margin-right: 2px; color: $muted;
  border-top-left-radius: 8px; border-top-right-radius: 8px; }
QTabBar::tab:hover { background: $hover; color: $text; }
QTabBar::tab:selected { background: $bg; color: $text; border-bottom: 2px solid $accent2; }
QTabBar::close-button { subcontrol-position: right; }
QSplitter::handle { background: $bg; }
QSplitter::handle:horizontal { width: 4px; } QSplitter::handle:vertical { height: 4px; }
QSplitter::handle:hover { background: $accent; }
QStatusBar { background: $panel; color: $muted; border-top: 1px solid $border; }
QStatusBar QLabel { color: $muted; padding: 0 6px; }
QDockWidget { color: $muted; }
QDockWidget::title { background: $panel; padding: 6px 10px; border-top: 1px solid $border; }
QDialog#palette { background: $panel; border: 1px solid $accent; border-radius: 14px; }
QCheckBox, QRadioButton { spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid $border;
  background: $input; }
QCheckBox::indicator { border-radius: 4px; } QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: $accent; border-color: $accent2; }
QProgressBar { background: $input; border: 1px solid $border; border-radius: 6px; text-align: center; color: $text;
  max-height: 14px; }
QProgressBar::chunk { border-radius: 5px;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $accent, stop:1 $accent2); }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle { background: $border; border-radius: 4px; min-height: 28px; min-width: 28px; }
QScrollBar::handle:hover { background: $accent; }
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { width: 0; height: 0;
  background: none; }
QToolTip { background: $panel; color: $text; border: 1px solid $accent; padding: 6px; border-radius: 6px; }
QGroupBox { border: 1px solid $border; border-radius: 10px; margin-top: 14px; padding: 12px 8px 8px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: $accent2; font-weight: 700; }
""")


def apply_theme(app, name: str) -> None:
    global CURRENT
    if name not in THEMES:
        name = "neon"
    CURRENT = name
    C.clear()
    C.update(THEMES[name])
    app.setStyle("Fusion")
    pal = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.WindowText, "text"), (QPalette.Base, "input"),
                      (QPalette.AlternateBase, "panel"), (QPalette.Text, "text"), (QPalette.Button, "panel2"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "sel"),
                      (QPalette.ToolTipBase, "panel"), (QPalette.ToolTipText, "text"),
                      (QPalette.Link, "accent2"), (QPalette.PlaceholderText, "muted")):
        pal.setColor(role, QColor(C[key]))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)
    app.setStyleSheet(STYLE.substitute(C))


def color(key: str) -> QColor:
    return QColor(C[key])
