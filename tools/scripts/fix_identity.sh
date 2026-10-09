#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
# VA_BITS=39: PAGE_OFFSET (linear map) = 0xffffffc000000000, cover 16GB
START=0xffffffc000000000ULL
END=0xffffffc400000000ULL
echo "identity range: $START .. $END"
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h \
  -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -DKERNELSNITCH_IDENTITY_START=$START \
  -DKERNELSNITCH_IDENTITY_END=$END \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock7 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock7 /mnt/e/Library/Desktop/ghostlock/ghostlock7_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock7_a64
