#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="$ROOT_DIR/dist"
mkdir -p "$OUT_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
BUNDLE_DIR="devlens_bundle_${STAMP}"
TARGET_DIR="$OUT_DIR/$BUNDLE_DIR"

mkdir -p "$TARGET_DIR"

cp -r src "$TARGET_DIR/"
cp -r scripts "$TARGET_DIR/"
cp -r docs "$TARGET_DIR/"
cp -r alembic "$TARGET_DIR/"
cp README.md "$TARGET_DIR/"
cp pyproject.toml "$TARGET_DIR/"
cp .env.example "$TARGET_DIR/" || true

tar -czf "$OUT_DIR/${BUNDLE_DIR}.tar.gz" -C "$OUT_DIR" "$BUNDLE_DIR"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$OUT_DIR/${BUNDLE_DIR}.tar.gz" > "$OUT_DIR/${BUNDLE_DIR}.tar.gz.sha256"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$OUT_DIR/${BUNDLE_DIR}.tar.gz" > "$OUT_DIR/${BUNDLE_DIR}.tar.gz.sha256"
fi

echo "bundle created: $OUT_DIR/${BUNDLE_DIR}.tar.gz"
if [[ -f "$OUT_DIR/${BUNDLE_DIR}.tar.gz.sha256" ]]; then
  echo "checksum: $OUT_DIR/${BUNDLE_DIR}.tar.gz.sha256"
fi
