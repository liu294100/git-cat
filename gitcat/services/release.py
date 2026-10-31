"""Release helpers: version detection/bumping in common project files and changelog updates."""
from __future__ import annotations

import datetime as _dt
import os
import re
from dataclasses import dataclass

from ..core.versioning import SEMVER_RE

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "release", "__pycache__", "target", ".tox"}


@dataclass
class VersionFile:
    path: str      # relative to repo root
    version: str
    pattern: str   # regex with exactly one group around the version


PATTERNS: list[tuple[str, str]] = [
    ("__init__.py", r"""(?m)^__version__\s*=\s*["']([^"']+)["']"""),
    ("_version.py", r"""(?m)^__version__\s*=\s*["']([^"']+)["']"""),
    ("version.py", r"""(?m)^(?:__version__|VERSION)\s*=\s*["']([^"']+)["']"""),
    ("package.json", r"""(?m)^\s{0,4}"version"\s*:\s*"([^"]+)\""""),
    ("pyproject.toml", r"""(?ms)^\[(?:project|tool\.poetry)\][^\[]*?^version\s*=\s*"([^"]+)\""""),
    ("Cargo.toml", r"""(?ms)^\[package\][^\[]*?^version\s*=\s*"([^"]+)\""""),
    ("setup.py", r"""version\s*=\s*["']([^"']+)["']"""),
    ("setup.cfg", r"""(?m)^version\s*=\s*([^\s]+)"""),
    ("build.gradle", r"""(?m)^version\s*=?\s*["']([^"']+)["']"""),
    ("VERSION", r"""^\s*v?([0-9][^\s]*)"""),
]


def detect_version_files(root: str, max_depth: int = 2) -> list[VersionFile]:
    res: list[VersionFile] = []
    names = {n for n, _ in PATTERNS}
    root = os.path.abspath(root)
    for cur, dirs, files in os.walk(root):
        depth = os.path.relpath(cur, root).count(os.sep) + (0 if cur == root else 1)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if depth >= max_depth:
            dirs[:] = []
        for fn in files:
            if fn not in names:
                continue
            full = os.path.join(cur, fn)
            try:
                with open(full, encoding="utf-8") as f:
                    text = f.read(256 * 1024)
            except (OSError, UnicodeDecodeError):
                continue
            for name, pat in PATTERNS:
                if name != fn:
                    continue
                m = re.search(pat, text)
                if m:
                    res.append(VersionFile(os.path.relpath(full, root).replace(os.sep, "/"), m.group(1), pat))
                    break
    res.sort(key=lambda v: (v.path.count("/"), v.path))
    return res


def write_version(root: str, vf: VersionFile, version: str) -> bool:
    full = os.path.join(root, vf.path)
    with open(full, encoding="utf-8", newline="") as f:
        text = f.read()
    m = re.search(vf.pattern, text)
    if not m:
        return False
    new = text[:m.start(1)] + version + text[m.end(1):]
    with open(full, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    return True


def bump(version: str, part: str) -> str:
    m = SEMVER_RE.match(version or "")
    if not m:
        return {"major": "1.0.0", "minor": "0.1.0"}.get(part, "0.0.1")
    a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if part == "major":
        return f"{a + 1}.0.0"
    if part == "minor":
        return f"{a}.{b + 1}.0"
    return f"{a}.{b}.{c + 1}"


def prepend_changelog(root: str, tag: str, notes: str) -> str:
    path = os.path.join(root, "CHANGELOG.md")
    today = _dt.date.today().isoformat()
    section = f"## {tag}\n\n_{today}_\n\n{notes.strip()}\n\n"
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old.startswith("# "):
        head, _, rest = old.partition("\n")
        new = head + "\n\n" + section + rest.lstrip("\n")
    else:
        new = "# Changelog\n\n" + section + old
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    return "CHANGELOG.md"


def notes_from_subjects(subjects: list[str]) -> str:
    groups: dict[str, list[str]] = {"feat": [], "fix": [], "other": []}
    for s in subjects:
        low = s.lower()
        if low.startswith(("feat", "add")):
            groups["feat"].append(s)
        elif low.startswith(("fix", "bug")):
            groups["fix"].append(s)
        elif not low.startswith(("bump version", "release", "merge")):
            groups["other"].append(s)
    lines = []
    for title, key in (("### Features", "feat"), ("### Fixes", "fix"), ("### Changes", "other")):
        if groups[key]:
            lines.append(title)
            lines += [f"- {s}" for s in groups[key]]
            lines.append("")
    return "\n".join(lines).strip()


WORKFLOW_TEMPLATE = """name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Extract release notes from CHANGELOG.md
        shell: bash
        run: |
          awk -v heading="## ${GITHUB_REF_NAME}" '
            $0 == heading { found = 1; next }
            found && /^## / { exit }
            found { print }
          ' CHANGELOG.md > release-notes.md 2>/dev/null || true
          touch release-notes.md
      # Add your build steps here and copy the artifacts to ./dist
      - name: Publish GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          files=$(ls dist/* 2>/dev/null || true)
          gh release create "$GITHUB_REF_NAME" $files --notes-file release-notes.md --generate-notes --verify-tag
"""


GITLAB_TEMPLATE = """stages: [build, release]

build:
  stage: build
  image: alpine:latest
  rules:
    - if: $CI_COMMIT_TAG =~ /^v/
  script:
    - mkdir -p dist
    - echo "Add your build steps here and write artifacts to ./dist"
  artifacts:
    paths: [dist/]

release:
  stage: release
  image: registry.gitlab.com/gitlab-org/release-cli:latest
  rules:
    - if: $CI_COMMIT_TAG =~ /^v/
  script:
    - awk -v heading="## $CI_COMMIT_TAG" '$0 == heading {f=1; next} f && /^## / {exit} f {print}' CHANGELOG.md > notes.md || true
    - touch notes.md
  release:
    tag_name: $CI_COMMIT_TAG
    name: $CI_COMMIT_TAG
    description: ./notes.md
"""

TEMPLATES = {
    "gitlab": (".gitlab-ci.yml", GITLAB_TEMPLATE),
    "gitea": (".gitea/workflows/release.yml", WORKFLOW_TEMPLATE.replace("gh release create", "echo release")),
}


def write_workflow_template(root: str, provider: str = "github") -> str:
    rel, body = TEMPLATES.get(provider, (".github/workflows/release.yml", WORKFLOW_TEMPLATE))
    full = os.path.join(root, rel)
    if os.path.exists(full):
        raise FileExistsError(rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    return rel
