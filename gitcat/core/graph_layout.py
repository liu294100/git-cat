"""Commit-graph lane layout (pure algorithm, O(commits x lanes))."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import Commit


@dataclass
class GraphRow:
    col: int
    color: int
    top: list[tuple[int, int, int]]     # (from_col, to_col, color): row top -> node centre
    bottom: list[tuple[int, int, int]]  # node centre -> row bottom
    width: int
    merge: bool


def layout(commits: list[Commit]) -> list[GraphRow]:
    lanes: list[Optional[str]] = []
    colors: list[int] = []
    next_color = 0
    rows: list[GraphRow] = []

    def alloc(sha: str) -> int:
        nonlocal next_color
        for i, v in enumerate(lanes):
            if v is None:
                lanes[i] = sha
                colors[i] = next_color
                next_color += 1
                return i
        lanes.append(sha)
        colors.append(next_color)
        next_color += 1
        return len(lanes) - 1

    for c in commits:
        hits = [i for i, v in enumerate(lanes) if v == c.sha]
        col = hits[0] if hits else alloc(c.sha)
        top = []
        for i, v in enumerate(lanes):
            if v is None:
                continue
            top.append((i, col, colors[i]) if v == c.sha else (i, i, colors[i]))
        node_color = colors[col]
        for i in hits[1:]:
            lanes[i] = None
        bottom = []
        fresh: set[int] = set()
        if c.parents:
            lanes[col] = c.parents[0]
            for p in c.parents[1:]:
                existing = [i for i, v in enumerate(lanes) if v == p]
                if existing:
                    pc = existing[0]
                else:
                    pc = alloc(p)
                    fresh.add(pc)
                bottom.append((col, pc, colors[pc]))
        else:
            lanes[col] = None
        for i, v in enumerate(lanes):
            if v is None or i in fresh:
                continue
            bottom.append((i, i, colors[i]))
        while lanes and lanes[-1] is None:
            lanes.pop()
            colors.pop()
        width = max([col] + [max(a, b) for a, b, _ in top + bottom]) + 1
        rows.append(GraphRow(col, node_color, top, bottom, width, len(c.parents) > 1))
    return rows
