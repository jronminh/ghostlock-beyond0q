#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
APC=0xffffff80080b2eec    # rt_mutex_adjust_prio_chain
API=0xffffff80080b2e34    # rt_mutex_adjust_pi
D() { aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
      --start-address=$1 --stop-address=$2 | sed -n '6,200p'; }
echo "===== rt_mutex_adjust_pi (full, 0xb8) ====="
D $API $((API+0xb8))
echo
echo "===== rt_mutex_adjust_prio_chain +0x1d0..+0x2b0 (fault at +0x244) ====="
D $((APC+0x1d0)) $((APC+0x2b0))
