# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec shared by Windows (onefile .exe) and macOS (.app bundle).
import sys

import os

IS_MAC = sys.platform == "darwin"
ICON = "assets/gitcat.icns" if IS_MAC else "assets/gitcat.ico"


def _version() -> str:
    for line in open(os.path.join("gitcat", "__init__.py"), encoding="utf-8"):
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip("\"'")
    return "0.0.0"


VERSION = _version()

# Windows file properties (Explorer → Properties → Details, Task Manager name and taskbar tooltip).
VERSION_FILE = None
if sys.platform == "win32":
    nums = [int(p) if p.isdigit() else 0 for p in (VERSION.split(".") + ["0", "0", "0"])[:4]]
    VERSION_FILE = os.path.join("build", "version_info.txt")
    os.makedirs("build", exist_ok=True)
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tuple(nums)}, prodvers={tuple(nums)}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'GitCat'),
      StringStruct('FileDescription', 'GitCat - Git client'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'GitCat'),
      StringStruct('LegalCopyright', 'GitCat contributors'),
      StringStruct('OriginalFilename', 'GitCat.exe'),
      StringStruct('ProductName', 'GitCat'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")

datas = [("assets", "assets"), ("gitcat/locales", "gitcat/locales")]
from PyInstaller.utils.hooks import collect_data_files  # noqa: E402
datas += collect_data_files("certifi")

# Qt modules GitCat never uses: excluding them keeps the bundle small and start-up fast.
EXCLUDES = [
    "tkinter", "unittest", "pydoc_data", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
    "PySide6.QtQuickWidgets", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtDBus",
    "PySide6.QtConcurrent", "PySide6.QtXml", "PySide6.QtHelp", "PySide6.QtDesigner", "PySide6.QtUiTools",
]

a = Analysis(
    ["run_gitcat.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GitCat",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICON],
    version=VERSION_FILE,
)

if IS_MAC:
    app = BUNDLE(
        exe,
        name="GitCat.app",
        icon=ICON,  # Dock, Finder and Cmd+Tab icon
        bundle_identifier="io.github.liu294100.gitcat",
        info_plist={
            "CFBundleName": "GitCat",
            "CFBundleDisplayName": "GitCat",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.developer-tools",
            "NSRequiresAquaSystemAppearance": False,
        },
    )
