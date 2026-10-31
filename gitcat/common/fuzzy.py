"""Sub-sequence fuzzy matching used by the command palette."""
from __future__ import annotations


def fuzzy_score(query: str, text: str) -> int:
    """Sub-sequence fuzzy match; bigger is better, -1 = no match."""
    q, tx = query.lower(), text.lower()
    if not q:
        return 0
    if q in tx:
        return 1000 - tx.index(q) - len(tx) // 10
    score, ti, prev = 0, 0, -2
    for ch in q:
        ti = tx.find(ch, ti)
        if ti < 0:
            return -1
        score += 10 if ti == prev + 1 else 1
        prev = ti
        ti += 1
    return score
