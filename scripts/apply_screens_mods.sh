#!/usr/bin/env bash
# Apply builder-side mods to the pinned seedsigner-lvgl-screens submodule:
#   deps/seedsigner-lvgl-screens-mods/new_files/  -> copied over the submodule tree
#   deps/seedsigner-lvgl-screens-mods/patches/*.patch -> `git apply`, in name order
#
# Idempotent: a patch that is already applied (reverse-applies cleanly) is skipped,
# so repeated local builds work. A patch that neither applies nor is already applied
# fails the build. Undo with:
#   git -C deps/seedsigner-lvgl-screens checkout -- . && git -C deps/seedsigner-lvgl-screens clean -fd components
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKDIR="${1:-$ROOT_DIR/deps}"
SCREENS_DIR="$WORKDIR/seedsigner-lvgl-screens"
MODS_DIR="$ROOT_DIR/deps/seedsigner-lvgl-screens-mods"

if [ ! -e "$SCREENS_DIR/.git" ]; then
  echo "ERROR: expected seedsigner-lvgl-screens repo at $SCREENS_DIR"
  exit 1
fi
[ -d "$MODS_DIR" ] || { echo "[screens-mods] none"; exit 0; }

if [ -d "$MODS_DIR/new_files" ]; then
  cp -R "$MODS_DIR/new_files/." "$SCREENS_DIR/"
  echo "[screens-mods] overlaid new_files/"
fi

shopt -s nullglob
for patch in "$MODS_DIR"/patches/*.patch; do
  name="$(basename "$patch")"
  if git -C "$SCREENS_DIR" apply --check "$patch" 2>/dev/null; then
    git -C "$SCREENS_DIR" apply "$patch"
    echo "[screens-mods] applied $name"
  elif git -C "$SCREENS_DIR" apply --reverse --check "$patch" 2>/dev/null; then
    echo "[screens-mods] already applied: $name"
  else
    echo "ERROR: [screens-mods] $name does not apply to $(git -C "$SCREENS_DIR" rev-parse --short HEAD)"
    git -C "$SCREENS_DIR" apply --check "$patch" || true
    exit 1
  fi
done
