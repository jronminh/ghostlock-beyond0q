#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
sed -i 's/#define P0_KERNEL_PHYS_LOAD 0xa8000000ULL/#define P0_KERNEL_PHYS_LOAD 0x80000000ULL/' src/core/target.h
grep -n 'P0_KERNEL_PHYS_LOAD' src/core/target.h
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock12 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock12 /mnt/e/Library/Desktop/ghostlock/ghostlock12_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock12_a64
