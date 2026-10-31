"""Input validation for git reference names."""
from __future__ import annotations

from typing import Optional

from ..common.i18n import t


def valid_ref_name(name: str) -> Optional[str]:
    bad = [" ", "~", "^", ":", "?", "*", "[", "\\", "..", "@{"]
    if not name:
        return t("err.name_empty")
    if any(b in name for b in bad) or name.startswith(("-", "/")) or name.endswith((".", "/", ".lock")):
        return t("err.name_invalid")
    return None
