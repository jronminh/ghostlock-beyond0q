#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### target.h PIPE_* ######"
grep -nE 'PIPE_' $R/target.h
echo
echo "###### pipe_physrw.c: offsets/fields dùng ######"
grep -nE 'PIPE_|nrbufs|curbuf|buffers|bufs|tmp_page|user|0x[0-9a-fA-F]{2,}' $R/pipe_physrw.c 2>/dev/null | head -50
echo
echo "###### disasm pipe_write: offsets on pipe_inode_info ######"
A=$(python3 - <<'PY'
import re
for l in open('/root/ghostlock/kernel/kallsyms_fixed.txt'):
    m=re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)',l)
    if m and m.group(3) in ('pipe_write','anon_pipe_write','pipe_read','pipe_resize_ring'):
        print(m.group(3), m.group(1))
PY
)
echo "$A"
for n in pipe_write pipe_read; do
  a=$(echo "$A" | awk -v n=$n '$1==n{print $2}')
  [ -z "$a" ] && continue
  printf -- "--- %s @ 0x%s ---\n" "$n" "$a"
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
    --start-address=0x$a --stop-address=$((0x$a+0x200)) \
    | grep -oE '\[x[0-9]+, #(0x[0-9a-f]+|[0-9]+)\]' | sort | uniq -c | sort -rn | head -20
done
