#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
sed -i 's/#define MM_STRUCT_SZ 0x370/#define MM_STRUCT_SZ 0x380/' src/core/common.h
grep -n 'define MM_STRUCT_SZ\|define MM_ORDER\|define MM_PARTIALS\|define KSNITCH_COLLISIONS' src/core/common.h
echo "=== rebuild ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -Isrc/core -Isrc/devices \
  -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock4 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock4 /mnt/e/Library/Desktop/ghostlock/ghostlock4_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock4_a64
