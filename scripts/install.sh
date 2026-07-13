#!/usr/bin/env bash
set -euo pipefail

error() {
    echo "install.sh error: $*" >&2
    exit 1
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAUNCHER_SRC="$SCRIPT_DIR/ai"
DEFAULT_TARGET="/Volumes/DISK h3r/AI/bin/ai"
TARGET="${1:-$DEFAULT_TARGET}"
TARGET_DIR="$(dirname "$TARGET")"

if [ ! -f "$LAUNCHER_SRC" ]; then
    error "Launcher script not found: $LAUNCHER_SRC"
fi

if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    error "ai-platform project root not found: $PROJECT_ROOT"
fi

chmod +x "$LAUNCHER_SRC"
mkdir -p "$TARGET_DIR"

if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
    rm -f "$TARGET"
fi

ln -s "$LAUNCHER_SRC" "$TARGET"

echo "Installed ai-platform launcher:"
echo "  $TARGET -> $LAUNCHER_SRC"
echo
echo "Project root:"
echo "  $PROJECT_ROOT"
echo
echo "Verify with:"
echo "  $TARGET --help"
echo "  $TARGET find договор"
echo "  $TARGET ask \"Где лежит последний договор займа по Химкам?\""
echo "  $TARGET analyze <file>"
echo "  $TARGET ingest"
