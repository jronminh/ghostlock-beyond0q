#!/bin/bash
cd ~/ghostlock || exit 1
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0xf11dc --stop-address=0xf2ddc 2>/dev/null > /tmp/dofutex.s
echo "=== bl targets (count) ==="
grep -oE '\sbl\s+[0-9a-f]+' /tmp/dofutex.s | awk '{print $2}' | sort | uniq -c | sort -rn | head -40 > /tmp/blt.txt
cat /tmp/blt.txt
echo
echo "=== map bl targets -> symbol names ==="
python3 - <<'PY'
sym={}
for line in open('/root/ghostlock/kernel/kallsyms_fixed.txt'):
    p=line.split()
    if len(p)>=3: sym[int(p[0],16)]=p[2]
def name(o):
    # nearest symbol <= o
    best=None
    for a,n in sym.items():
        if a<=o and (best is None or a>best): best=a
    return sym.get(best,'?') if best is not None else '?'
for line in open('/tmp/blt.txt'):
    parts=line.split()
    if len(parts)>=2:
        print("%4s  %s  -> %s" % (parts[0], parts[1], name(int(parts[1],16))))
PY
echo
echo "=== find bl to rt_mutex_start_proxy_lock (0xb3efc) / adjust_prio_chain (0xb2eec) ==="
grep -nE 'bl\s+(b3efc|b2eec)' /tmp/dofutex.s
