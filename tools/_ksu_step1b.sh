#!/bin/bash
S=/root/ghostlock/src/g9700
O=$S/out
echo "==Makefile CC bits=="
grep -nE 'gcc-wrapper|REAL_CC|llvm-arm-toolchain|^CC[ \t:=]|^CROSS_COMPILE' "$S/Makefile" | head -30
echo "==which python2=="
which python2 python2.7 2>&1
echo "==try gcc override modules_prepare=="
make -s -C "$S" O="$O" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  CC=aarch64-linux-gnu-gcc LD=aarch64-linux-gnu-ld modules_prepare 2>&1 | tail -30
echo "prep_rc=${PIPESTATUS[0]}"
ls -la "$O/Module.symvers" 2>&1
