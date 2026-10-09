#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
python3 - <<'PY'
p='src/core/kernelsnitch/kernelsnitch.h'
s=open(p).read()
anchor='    size_t approx_time = MIN(__measure((size_t)&ks->futexes[0]), __measure((size_t)&ks->futexes[KS_PAGE_SIZE+8]));'
assert anchor in s, "anchor not found"
s=s.replace(anchor, anchor + '\n    pr_info("approx_time(baseline)=%zu\\n", approx_time);')
# print the heavy-bucket time after filling
anchor2='    __increase(ks, ID, APPENDED_FUTEXES);'
assert anchor2 in s, "anchor2 not found"
s=s.replace(anchor2, anchor2 + '\n    pr_info("heavy_time(inc_futex[ID])=%zu\\n", __measure((size_t)&ks->inc_futex[ID]));')
open(p,'w').write(s)
print("patched")
PY
grep -n 'approx_time(baseline)\|heavy_time' src/core/kernelsnitch/kernelsnitch.h
echo "=== rebuild (MULT=30) ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock6 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock6 /mnt/e/Library/Desktop/ghostlock/ghostlock6_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock6_a64
