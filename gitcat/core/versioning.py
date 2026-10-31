"""Semantic-version helpers shared by the tag UI and the release service."""
from __future__ import annotations

import re


SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(.*)$")


def semver_key(tag: str) -> tuple:
    m = SEMVER_RE.match(tag)
    if not m:
        return (-1, -1, -1, tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) == "", m.group(4))
