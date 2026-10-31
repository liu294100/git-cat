#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/../.."

cd "$ROOT"
[[ -x .venv/bin/python ]] || python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-build.txt
.venv/bin/python -m PyInstaller --noconfirm --clean GitCat.spec
echo "Build completed in: $ROOT/dist"
