#!/bin/bash
K=/root/ghostlock/kernel
IMG=$K/Image; BASE=0xffffff8008000000
for n in SyS_nanosleep hrtimer_nanosleep do_nanosleep; do
  a=$(grep -nE " $n$" $K/kallsyms_fixed.txt | head -1 | cut -d: -f2 | cut -c1-16)
  [ -z "$a" ] && { echo "$n: (not found)"; continue; }
  echo "--- $n @ 0x$a ---"
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
    --start-address=0x$a --stop-address=$((0x$a+0x40)) | sed -n '6,20p'
done
