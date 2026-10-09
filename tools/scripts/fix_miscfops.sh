#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
sed -i 's/#define ASHMEM_MISC_FOPS_OFF   0x02BB1750ULL/#define ASHMEM_MISC_FOPS_OFF   0x02BB1760ULL/' src/core/target.h
grep -n 'ASHMEM_MISC_FOPS_OFF' src/core/target.h
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock13 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock13 /mnt/e/Library/Desktop/ghostlock/ghostlock13_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock13_a64
