#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
echo "=== prepare with CC=gcc (bypass clang wrapper) ==="
make O=out CC=aarch64-linux-gnu-gcc HOSTCC=gcc prepare 2>&1 | grep -v 'python2: No such' | tail -30
echo
echo "=== headers? ==="
ls -la out/include/generated/autoconf.h out/include/generated/bounds.h out/arch/arm64/include/generated/asm-offsets.h 2>&1
