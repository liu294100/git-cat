"""Fail if any translation key used in code is missing, or locales differ in keys/placeholders."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "gitcat" / "locales"
KEY_RE = re.compile(r't\(\s*"([a-z_]+\.[a-z0-9_.]+)"')
FMT_RE = re.compile(r"\{(\w+)\}")


def main() -> int:
    used = set()
    for py in (ROOT / "gitcat").rglob("*.py"):
        used |= set(KEY_RE.findall(py.read_text(encoding="utf-8")))
    en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
    errors = [f"en.json is missing '{k}'" for k in sorted(used - set(en))]
    for path in sorted(LOCALES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        errors += [f"{path.name}: missing '{k}'" for k in sorted(set(en) - set(data))]
        errors += [f"{path.name}: unknown '{k}'" for k in sorted(set(data) - set(en))]
        errors += [f"{path.name}: placeholders differ in '{k}'" for k in data
                   if k in en and set(FMT_RE.findall(data[k])) != set(FMT_RE.findall(en[k]))]
    for e in errors:
        print(e)
    print(f"{len(list(LOCALES.glob('*.json')))} locales, {len(en)} keys, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
