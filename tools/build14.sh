#!/bin/bash
# Build the ghostlock driver from THIS repo (deep fork for beyond0q) in WSL.
# Usage:  bash tools/build14.sh [outname]      -> <repo>/<outname>_a64
# The repo is the source of truth; nothing outside it is compiled.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c \
src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c \
src/tools/glshell.c"
OUT=${1:-/tmp/ghostlock}

echo "=== build: $ROOT -> $OUT ==="
if ! aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
      -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC \
      -o "$OUT" -static -pthread 2>/tmp/gl_build.err; then
  echo "=== BUILD FAILED ==="
  grep -iE 'error' /tmp/gl_build.err | head -40
  exit 1
fi

file "$OUT"
cp -f "$OUT" "$ROOT/$(basename "$OUT")_a64"
echo "=== ok: $ROOT/$(basename "$OUT")_a64 ==="
ls -la "$ROOT/$(basename "$OUT")_a64"
