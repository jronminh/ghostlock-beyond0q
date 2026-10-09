#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
D() { aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
      --start-address=$1 --stop-address=$2 | sed -n '6,200p'; }
echo "===== SyS_futex (native) 0xffffff80080f507c ====="
D 0xffffff80080f507c 0xffffff80080f5120
echo
echo "===== compat_SyS_setsockopt 0xffffff8009482fdc ====="
D 0xffffff8009482fdc 0xffffff80094830c0
