#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### target.h ASHMEM/CONFIGFS symbol offsets (từ bảng device) ######"
grep -nE 'off_configfs|off_ashmem|ASHMEM_|CONFIGFS_' $R/devices/beyond0q/offsets.h | head
echo
echo "###### disasm configfs_bin_write_iter: field offsets on the buffer (x19/x20...) ######"
A=$(python3 - <<'PY'
import re,bisect
syms=[]
for l in open('/root/ghostlock/kernel/kallsyms_fixed.txt'):
    m=re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)',l)
    if m: syms.append((int(m.group(1),16),m.group(3)))
syms.sort()
for n in ('configfs_bin_write_iter','configfs_read_iter','configfs_write_file'):
    for a,t in syms:
        if t==n: print(n,hex(a)); break
PY
)
echo "$A"
for pair in $(echo "$A" | awk '{print $2}'); do :; done
for n in configfs_bin_write_iter configfs_read_iter; do
  a=$(echo "$A" | awk -v n=$n '$1==n{print $2}')
  [ -z "$a" ] && continue
  echo "--- $n @ $a ---"
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
    --start-address=$a --stop-address=$((a+0x140)) \
    | grep -oE '\[x[0-9]+, #(0x[0-9a-f]+|[0-9]+)\]|\[x[0-9]+\]' | sort | uniq -c | sort -rn | head -25
done
