#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
VERSION="${1:-}"

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [version]" >&2
  exit 2
fi
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "release.sh must run on macOS because macOS application bundles cannot be cross-built." >&2
  exit 2
fi
if [[ -z "$VERSION" ]]; then
  VERSION="$(sed -nE 's/^__version__[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' \
    "$ROOT/gitcat/__init__.py" | head -n 1)"
fi
if [[ ! "$VERSION" =~ ^[0-9A-Za-z][0-9A-Za-z._-]*$ ]]; then
  echo "Invalid or missing version: $VERSION" >&2
  exit 2
fi

case "$(uname -m)" in
  x86_64) ARCH="x64" ;;
  arm64|aarch64) ARCH="arm64" ;;
  *) ARCH="$(uname -m)" ;;
esac

RELEASE_DIR="$ROOT/release"
PACKAGE_DIR="$RELEASE_DIR/GitCat-macOS-${ARCH}-onefile-v${VERSION}"
ZIP_PATH="$PACKAGE_DIR.zip"
APP="$ROOT/dist/GitCat.app"
mkdir -p "$RELEASE_DIR"

echo "Building macOS application bundle..."
"$ROOT/scripts/macos/build.sh"
if [[ ! -d "$APP" ]]; then
  echo "Expected application bundle not found: $APP" >&2
  exit 1
fi

# Ad-hoc signature so Apple Silicon will launch the bundle (no developer certificate required).
codesign --force --deep --sign - "$APP" || echo "warning: ad-hoc codesign failed" >&2

rm -rf -- "$PACKAGE_DIR" "$ZIP_PATH"
mkdir -p "$PACKAGE_DIR"
cp -R "$APP" "$PACKAGE_DIR/"
cp "$ROOT"/README*.md "$ROOT/CHANGELOG.md" "$ROOT/assets/gitcat.png" "$PACKAGE_DIR/"
[[ -f "$ROOT/LICENSE" ]] && cp "$ROOT/LICENSE" "$PACKAGE_DIR/"
cat > "$PACKAGE_DIR/Quick-Start.txt" <<EOF
GitCat v$VERSION

1. Move GitCat.app to /Applications (or anywhere you can write, so auto-update works).
2. First launch: right-click GitCat.app > Open, because the app is not notarized.
3. Git must be installed (Xcode Command Line Tools: xcode-select --install, or Homebrew).
4. Configuration is stored in ~/Library/Application Support/GitCat/config.json.
EOF

/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$PACKAGE_DIR" "$ZIP_PATH"
echo "Created: $ZIP_PATH"
