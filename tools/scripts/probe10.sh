#!/bin/bash
K=/root/ghostlock/kernel
IMG=$K/Image
BASE=0xffffff8008000000
echo "=== requeue symbols ==="
grep -nE 'requeue' $K/kallsyms_fixed.txt | head
echo "=== other users of sizeof(unsigned long) for kernel words ==="
grep -rn "sizeof(unsigned long)" /root/ghostlock/ghostlock-oneplus/src/core/*.c
D() { aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
      --start-address=$1 --stop-address=$2 | sed -n '6,120p'; }
echo "=== compat_SyS_futex 0xffffff80080f53fc (frame) ==="
D 0xffffff80080f53fc 0xffffff80080f5460
echo "=== do_futex 0xffffff80080f11dc head ==="
D 0xffffff80080f11dc 0xffffff80080f12a0
