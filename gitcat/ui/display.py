"""Presentation helpers shared by widgets: status letters/colours and avatar colours."""
from __future__ import annotations

import hashlib

from ..common.i18n import t
from ..core.models import FileChange


STATUS_COLOR = {"M": "#fbbf24", "A": "#34d399", "D": "#ff5c8a", "R": "#22d3ee", "C": "#22d3ee", "T": "#c084fc",
                "?": "#34d399", "U": "#ff3b6b"}


def status_text(letter: str) -> str:
    return t({"M": "st.modified", "A": "st.added", "D": "st.deleted", "R": "st.renamed", "C": "st.copied",
              "T": "st.type", "?": "st.untracked", "U": "st.conflict"}.get(letter, "st.modified"))


def status_letter(fc: FileChange, staged: bool) -> str:
    if fc.conflicted:
        return "U"
    if fc.untracked:
        return "?"
    return fc.x if staged else fc.y


AVATAR_COLORS = ["#8b5cf6", "#22d3ee", "#f472b6", "#34d399", "#fbbf24", "#60a5fa", "#f97316", "#a3e635",
                 "#e879f9", "#2dd4bf", "#fb7185", "#818cf8"]


def avatar_color(seed: str) -> str:
    h = int(hashlib.md5(seed.lower().encode("utf-8")).hexdigest()[:6], 16)  # noqa: S324
    return AVATAR_COLORS[h % len(AVATAR_COLORS)]
