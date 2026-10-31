"""Unified-diff parsing and partial (hunk / line) patch construction."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


HUNK_RE = re.compile(rb"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


@dataclass
class Hunk:
    old_start: int
    new_start: int
    tail: bytes
    lines: list[bytes] = field(default_factory=list)


@dataclass
class ParsedDiff:
    header: list[bytes] = field(default_factory=list)
    hunks: list[Hunk] = field(default_factory=list)
    binary: bool = False
    files: int = 0
    added: int = 0
    removed: int = 0


def parse_diff(data: bytes) -> ParsedDiff:
    pd = ParsedDiff()
    cur: Optional[Hunk] = None
    for line in data.split(b"\n"):
        if line.startswith(b"diff --git") or line.startswith(b"diff --cc"):
            pd.files += 1
            cur = None
        m = HUNK_RE.match(line)
        if m:
            cur = Hunk(int(m.group(1)), int(m.group(3)), m.group(5))
            pd.hunks.append(cur)
            continue
        if cur is None:
            if line.startswith(b"Binary files") or line.startswith(b"GIT binary patch"):
                pd.binary = True
            if pd.files <= 1:
                pd.header.append(line)
            continue
        if line[:1] in (b" ", b"+", b"-", b"\\"):
            cur.lines.append(line)
            if line[:1] == b"+":
                pd.added += 1
            elif line[:1] == b"-":
                pd.removed += 1
        elif line == b"":
            continue
        else:
            cur = None
            if pd.files <= 1:
                pd.header.append(line)
    while pd.header and pd.header[-1] == b"":
        pd.header.pop()
    return pd


def build_patch(pd: ParsedDiff, selection: dict[int, Optional[set[int]]], reverse: bool) -> bytes:
    """selection: hunk index -> selected line indexes (None = whole hunk).
    reverse=False: forward apply (stage). Unselected '-' become context, unselected '+' dropped.
    reverse=True: reverse apply (unstage/discard). Unselected '+' become context, unselected '-' dropped."""
    out = list(pd.header)
    produced = False
    for hi in sorted(selection):
        h = pd.hunks[hi]
        sel = selection[hi]
        new_lines: list[bytes] = []
        old_n = new_n = 0
        changed = False
        dropped_prev = False
        for li, line in enumerate(h.lines):
            tch = line[:1]
            if tch == b"\\":
                if not dropped_prev:
                    new_lines.append(line)
                continue
            dropped_prev = False
            chosen = sel is None or li in sel
            if tch == b" ":
                new_lines.append(line)
                old_n += 1
                new_n += 1
            elif tch == b"-":
                if chosen:
                    new_lines.append(line)
                    old_n += 1
                    changed = True
                elif not reverse:
                    new_lines.append(b" " + line[1:])
                    old_n += 1
                    new_n += 1
                else:
                    dropped_prev = True
            elif tch == b"+":
                if chosen:
                    new_lines.append(line)
                    new_n += 1
                    changed = True
                elif reverse:
                    new_lines.append(b" " + line[1:])
                    old_n += 1
                    new_n += 1
                else:
                    dropped_prev = True
        if not changed:
            continue
        produced = True
        out.append(b"@@ -%d,%d +%d,%d @@%s" % (h.old_start, old_n, h.new_start, new_n, h.tail))
        out.extend(new_lines)
    if not produced:
        return b""
    return b"\n".join(out) + b"\n"
