"""Repository statistics derived from commit lists."""
from __future__ import annotations

from datetime import datetime

from .models import Commit


def timeline_from(commits: list[Commit], months: int = 12) -> list[tuple[str, int]]:
    buckets: dict[str, int] = {}
    for c in commits:
        key = datetime.fromtimestamp(c.timestamp).strftime("%Y-%m")
        buckets[key] = buckets.get(key, 0) + 1
    keys = sorted(buckets)[-months:]
    return [(k, buckets[k]) for k in keys]
