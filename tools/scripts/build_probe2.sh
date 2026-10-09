#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
echo "=== build probe object ==="
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_offsets.o 2>&1 | grep -v 'python2: No such' | tail -30
echo
OBJ=out/kernel/probe_offsets.o
ls -la $OBJ 2>&1
echo
echo "=== dump const data (offset values) ==="
aarch64-linux-gnu-objdump -s -j .rodata $OBJ 2>/dev/null
aarch64-linux-gnu-objdump -s -j .data $OBJ 2>/dev/null
return 0 2>/dev/null || true
