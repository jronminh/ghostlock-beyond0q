#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
echo "=== compile ==="
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -Isrc/core -Isrc/devices \
  -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock -static -pthread 2>&1 | head -40
echo "---"
ls -la /tmp/ghostlock 2>/dev/null && file /tmp/ghostlock
