#!/bin/bash
set -e
cd ~/ghostlock/ghostlock-oneplus || exit 1
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
OUT=${1:-/tmp/ghostlock14}
echo "=== compile -> $OUT ==="
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC \
  -o "$OUT" -static -pthread 2>&1 | grep -iE 'error' | head -20 || true
ls -la "$OUT" && file "$OUT"
cp -f "$OUT" /mnt/e/Library/Desktop/ghostlock/$(basename "$OUT")_a64
ls -la /mnt/e/Library/Desktop/ghostlock/$(basename "$OUT")_a64
