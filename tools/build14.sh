#!/bin/bash
# Build the ghostlock driver + the `dnroot` UMH payload from THIS repo (WSL).
# Usage:  bash tools/build14.sh [outname]
#   -> <repo>/<outname>_a64          (driver)
#   -> <repo>/<outname>_dnroot_a64   (UMH payload)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DRIVER_SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c \
src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c \
src/tools/glshell.c src/primitives/rootshell.c"
DNROOT_SRC="src/payload/dnroot.c src/primitives/rootshell.c"

OUT=${1:-/tmp/ghostlock}
BASE="$(basename "$OUT")"

echo "=== build driver: $ROOT -> $OUT ==="
if ! aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
      -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' \
      $DRIVER_SRC -o "$OUT" -static -pthread 2>/tmp/gl_build.err; then
  echo "=== DRIVER BUILD FAILED ==="; grep -iE 'error' /tmp/gl_build.err | head -40; exit 1
fi
file "$OUT"
cp -f "$OUT" "$ROOT/${BASE}_a64"

echo "=== build dnroot: -> ${OUT}_dnroot ==="
if ! aarch64-linux-gnu-gcc -O2 -w -include stddef.h \
      -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' \
      $DNROOT_SRC -o "${OUT}_dnroot" -static 2>/tmp/gl_build_dnroot.err; then
  echo "=== DNROOT BUILD FAILED ==="; grep -iE 'error' /tmp/gl_build_dnroot.err | head -40; exit 1
fi
file "${OUT}_dnroot"
cp -f "${OUT}_dnroot" "$ROOT/${BASE}_dnroot_a64"

echo "=== ok ==="
ls -la "$ROOT/${BASE}_a64" "$ROOT/${BASE}_dnroot_a64"
