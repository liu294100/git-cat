"""Internationalisation: JSON catalogues in gitcat/locales, English fallback."""
from __future__ import annotations

import json
import locale
from pathlib import Path

LANGUAGES: dict[str, str] = {
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "es": "Español",
    "pt": "Português",
    "th": "ไทย",
    "ms": "Bahasa Melayu",
    "ru": "Русский",
}

_current = "en"
_catalog: dict[str, str] = {}
_fallback: dict[str, str] = {}


def locales_dir() -> Path:
    from .resources import resource_path
    return resource_path("gitcat/locales")


def _load(code: str) -> dict[str, str]:
    try:
        with open(locales_dir() / f"{code}.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def detect_system_language() -> str:
    candidates = []
    try:
        from PySide6.QtCore import QLocale
        candidates.append(QLocale.system().name())
    except Exception:  # noqa: BLE001
        pass
    try:
        candidates.append(locale.getlocale()[0] or "")
    except ValueError:
        pass
    for name in candidates:
        code = (name or "").replace("-", "_").split("_")[0].lower()
        if code in LANGUAGES:
            return code
        low = (name or "").lower()
        for key, native in (("chinese", "zh"), ("japanese", "ja"), ("korean", "ko"), ("french", "fr"),
                            ("spanish", "es"), ("portuguese", "pt"), ("thai", "th"), ("malay", "ms"),
                            ("russian", "ru")):
            if low.startswith(key):
                return native
    return "en"


def set_language(code: str) -> str:
    global _current, _catalog, _fallback
    if code not in LANGUAGES:
        code = detect_system_language()
    _current = code
    _fallback = _load("en")
    _catalog = _fallback if code == "en" else _load(code)
    return code


def current_language() -> str:
    return _current


def t(key: str, **kw) -> str:
    text = _catalog.get(key) or _fallback.get(key) or key
    if kw:
        try:
            return text.format(**kw)
        except (KeyError, IndexError, ValueError):
            return text
    return text
