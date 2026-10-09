#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
R=/root/ghostlock/ghostlock-oneplus/src
echo "###### beyond0q: off_configfs_* / off_ashmem_* ######"
grep -nE 'off_configfs|off_ashmem_' $R/devices/beyond0q/offsets.h
echo
for pair in "configfs_read_iter:0x002BE7DC" "configfs_bin_write_iter:0x002BE96C"; do
  n=${pair%%:*}; o=${pair##*:}
  a=$((0xffffff8008000000 + o))
  printf "--- %s @ %s ---\n" "$n" "$(printf '0x%x' $a)"
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
    --start-address=$a --stop-address=$((a+0x190)) \
    | grep -oE '\[x[0-9]+, #(0x[0-9a-f]+|[0-9]+)\]|\[x[0-9]+, x[0-9]+' | sort | uniq -c | sort -rn | head -30
done
