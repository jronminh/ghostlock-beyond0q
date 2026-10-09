#!/bin/bash
IMG=~/ghostlock/kernel/Image
BASE=0xffffff8008000000
scan() {
  local nm=$1 a=$2 b=$3
  echo "=== $nm ($a .. $b) ==="
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
    --start-address=$((BASE + a)) --stop-address=$((BASE + b)) 2>/dev/null \
    | grep -nE 'sub[[:space:]]+sp, sp, #0x|add[[:space:]]+x[0-9]+, sp, #0x|9426ef4|move_addr' | head -30
  echo
}
scan sendto   0x1428b54 0x1428d9c
scan recvfrom 0x1428d9c 0x1428f54
scan recvmsg  0x14299b4 0x1429c00
