#!/bin/bash
# Compile kernel/workqueue.c with -g and extract struct member offsets from DWARF.
set -e
G="$HOME/ghostlock/src/g9700"
cd "$G/out"
aarch64-linux-gnu-gcc -nostdinc -isystem /usr/lib/gcc-cross/aarch64-linux-gnu/14/include \
  -I../arch/arm64/include -I./arch/arm64/include/generated -I../include -I./include \
  -I../arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I../include/uapi \
  -I./include/generated/uapi -include ../include/linux/kconfig.h -I../kernel -Ikernel \
  -D__KERNEL__ -mlittle-endian -DKASAN_SHADOW_SCALE_SHIFT=3 -fno-strict-aliasing -fno-common \
  -fshort-wchar -std=gnu89 -fno-PIE -mgeneral-regs-only -DCONFIG_AS_LSE=1 \
  -fno-asynchronous-unwind-tables -mpc-relative-literal-loads -fno-pic -mabi=lp64 \
  -fno-delete-null-pointer-checks -O2 -fno-var-tracking-assignments -fno-jump-tables \
  -fno-strict-overflow -fno-merge-all-constants -fmerge-constants -g \
  -DKBUILD_BASENAME='"workqueue"' -DKBUILD_MODNAME='"workqueue"' \
  -c -o /tmp/workqueue.o ../kernel/workqueue.c 2>/tmp/wq.err || true
if [ ! -s /tmp/workqueue.o ]; then echo "COMPILE FAILED"; head -20 /tmp/wq.err; exit 1; fi
echo "compiled: $(ls -la /tmp/workqueue.o | awk '{print $5}') bytes"
