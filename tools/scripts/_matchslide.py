#!/usr/bin/env python3
import bisect
KIMAGE = 0xffffff8008000000
IPS = [0xffffff8009771c20,0xffffff800809bbd4,0xffffff8009771c30,0xffffff8009791c5c,
       0xffffff800824188c,0xffffff80081797bc,0xffffff80080f5728,0xffffff8009771268]
syms=[]
for line in open("/root/ghostlock/kernel/kallsyms_fixed.txt"):
    p=line.split()
    if len(p)>=3:
        try: a=int(p[0],16)
        except: continue
        syms.append((a,p[2],p[1]))   # (addr,name,type)
syms.sort()
A=[s[0] for s in syms]
def cont(va):
    i=bisect.bisect_right(A,va)-1
    if i<0: return None
    return syms[i], va-syms[i][0]
print("sanity rb_erase_cached@0xffffff80096e7a6c ->", cont(0xffffff80096e7a6c))
print("sanity SyS_setsockopt@0xffffff8009428f54 ->", cont(0xffffff8009428f54))
for S in range(0, 0x4000001, 0x8000):
    r0=cont(IPS[0]-S)
    if not r0: continue
    (a,n,t),off=r0
    r1=cont(IPS[1]-S)
    r2=cont(IPS[3]-S)
    if any(k in n for k in ("copy","user","memcpy","read","write","clear")) or off<0x400:
        print("S=%#09x  dom=%-34s off=%#06x [%s]   #2=%-26s   #4=%s" % (
            S, n, off, t,
            (r1[0][1] if r1 else "?"), (r2[0][1] if r2 else "?")))
