#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
D() { aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
      --start-address=$1 --stop-address=$2 | sed -n '6,400p'; }
SS=0xffffff800942eafc     # sock_setsockopt
echo "===== sock_setsockopt: frame + 0xfe/0x3e8/0x100 refs ====="
D $SS $((SS+0x700)) > /tmp/ss.asm
grep -nE 'sub[[:space:]]+sp|#0xfe|#0x3e8|#0x100|copy_from_user|#1000' /tmp/ss.asm | head -40
echo
echo "----- first 40 lines -----"
sed -n '1,40p' /tmp/ss.asm
echo
echo "===== do_notify_resume 0xffffff800800a94c ====="
D 0xffffff800800a94c 0xffffff800800aa40
