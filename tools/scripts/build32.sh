#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
OUT=${1:-/tmp/ghostlock32}
echo "=== armhf compile -> $OUT ==="
arm-linux-gnueabihf-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 -DCOMPAT32 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC \
  -o "$OUT" -static -pthread 2>&1 | head -40
echo "rc=$?"
ls -la "$OUT" 2>/dev/null && file "$OUT"
