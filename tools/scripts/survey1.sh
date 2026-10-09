#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
APC=0xffffff80080b2eec
K=/root/ghostlock/src/g9700/kernel
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "########## 1) 4.14 SOURCE: rt_mutex_adjust_prio_chain ##########"
sed -n '/^static int rt_mutex_adjust_prio_chain/,/^}/p' $K/locking/rtmutex.c
echo
echo "########## 2) DISASM offsets: loads [reg,#off] in adjust_prio_chain ##########"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
  --start-address=$APC --stop-address=$((APC+0x830)) | sed -n '6,600p' > /tmp/apc.asm
grep -nE '\b(ldr|str|ldur|stur|ldp|stp)\b' /tmp/apc.asm | head -120
