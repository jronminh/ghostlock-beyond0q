#!/bin/bash
cd ~/ghostlock || exit 1
grep -oE 'bl\s+0x[0-9a-f]+' /tmp/dofutex.s | awk '{print $2}' | sort | uniq -c | sort -rn > /tmp/blt.txt
echo "=== all distinct bl targets in do_futex, mapped ==="
python3 - <<'PY'
BASE=0xffffff8008000000
syms=[]
for line in open('/root/ghostlock/kernel/kallsyms_fixed.txt'):
    p=line.split()
    if len(p)>=3:
        syms.append((int(p[0],16), p[2]))
syms.sort()
import bisect
addrs=[a for a,_ in syms]
def name(off):
    va=off+BASE
    i=bisect.bisect_right(addrs,va)-1
    return syms[i][1] if i>=0 else '?'
for line in open('/tmp/blt.txt'):
    p=line.split()
    if len(p)>=2:
        off=int(p[1],16)
        print("%4s  0x%-8x -> %s" % (p[0], off, name(off)))
PY
echo
echo "=== exact call to rt_mutex_start_proxy_lock (0xb3efc) ? ==="
grep -nE 'bl\s+0xb3efc' /tmp/dofutex.s || echo "NONE"
echo
echo "=== context lines: instructions referencing sp+0x90 or 0xd0 near rtmutex calls ==="
grep -nE 'add\s+x[0-9]+, sp, #0x(90|d0)|bl\s+0xb[0-9a-f]{4}' /tmp/dofutex.s | head -40
