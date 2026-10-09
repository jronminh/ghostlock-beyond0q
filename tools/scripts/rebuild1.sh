#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
echo "=== before ==="
grep -n 'define MM_STRUCT_SZ\|define MM_ORDER\|define KSNITCH_COLLISIONS' src/core/common.h
sed -i 's/#define MM_STRUCT_SZ 0x500/#define MM_STRUCT_SZ 0x370/' src/core/common.h
echo "=== after ==="
grep -n 'define MM_STRUCT_SZ\|define MM_ORDER\|define KSNITCH_COLLISIONS' src/core/common.h
echo
echo "=== rebuild ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -Isrc/core -Isrc/devices \
  -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock2 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock2 /mnt/e/Library/Desktop/ghostlock/ghostlock2_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock2_a64
