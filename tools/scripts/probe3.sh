#!/bin/bash
K=/root/ghostlock/kernel
echo "--- kallsyms ---"
grep -nE '_raw_spin_trylock$|rt_mutex_adjust_prio_chain$|rt_mutex_adjust_pi$|_stext$|_text$|__sched_setscheduler$|SyS_sched_setattr$' $K/kallsyms_fixed.txt
echo "--- find _raw_spin_trylock byte pattern in Image ---"
python3 - <<'PY'
data=open('/root/ghostlock/kernel/Image','rb').read()
# prologue bytes of _raw_spin_trylock at +0x0c..: d5384108 b9404909 11000529 b9004909 885ffc09
pat=bytes.fromhex('084138d5094940b929050011094900b909fc5f88')
i=data.find(pat)
print('pattern file offset:', hex(i) if i>=0 else None, 'size', len(data))
if i>=0:
    print('=> function base (pattern-0x0c) file offset', hex(i-0x0c))
    print('   if Image base = 0xffffff8008000000 -> vaddr', hex(0xffffff8008000000 + i-0x0c))
    print('   if Image base = 0xffffff8008080000 -> vaddr', hex(0xffffff8008080000 + i-0x0c))
PY
