#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
python3 - <<'PY'
import re,io
p='src/core/kernelsnitch/kernelsnitch.h'
s=open(p).read()
s=s.replace('#define REPEAT_MEASUREMENT 128','#define REPEAT_MEASUREMENT 256')
s=s.replace('#define AVERAGE (1<<3)','#define AVERAGE (1<<4)')
# print approx_time and per-collision time
if 'approx_time=%zu' not in s:
    s=s.replace('        __increase(ks, ID, APPENDED_FUTEXES);',
                '        pr_info("approx_time=%zu\\n", approx_time);\n        __increase(ks, ID, APPENDED_FUTEXES);')
    s=s.replace('            if (ks->verbose) pr_info("  %016zx\\n", futex_addr);',
                '            if (ks->verbose) pr_info("  %016zx t=%zu\\n", futex_addr, ks->times[i]);')
open(p,'w').write(s)
print("patched kernelsnitch.h")
PY
grep -n 'REPEAT_MEASUREMENT 256\|AVERAGE (1<<4)\|approx_time=%zu\|t=%zu' src/core/kernelsnitch/kernelsnitch.h
# verbose on
sed -i 's/MM_STRUCT_SZ, MM_ORDER, cpu_count, KSNITCH_COLLISIONS, 0, 0/MM_STRUCT_SZ, MM_ORDER, cpu_count, KSNITCH_COLLISIONS, 1, 0/' src/core/util.c
grep -n 'KSNITCH_COLLISIONS, 1, 0' src/core/util.c
echo "=== rebuild (MULT=30) ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock5 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock5 /mnt/e/Library/Desktop/ghostlock/ghostlock5_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock5_a64
