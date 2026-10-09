#!/usr/bin/env python3
import bisect
KIMAGE = 0xffffff8008000000
IPS = [
 (0xffffff8009771c20,2703),(0xffffff800809bbd4,377),(0xffffff8009771c30,274),
 (0xffffff8009771c40,180),(0xffffff8009771c50,172),(0xffffff8009791c5c,136),
 (0xffffff8009771c04,110),(0xffffff800824188c,96),(0xffffff8009771c54,79),
 (0xffffff8009771c1c,77),(0xffffff8009771334,66),(0xffffff80081797bc,64),
 (0xffffff80084e1d34,59),(0xffffff8008219d90,58),(0xffffff8009771c48,58),
 (0xffffff80080f5728,57),(0xffffff80084b1f90,57),(0xffffff8009771268,55),
]
syms=[]
for line in open("/root/ghostlock/kernel/kallsyms_fixed.txt"):
    p=line.split()
    if len(p)>=3:
        try: a=int(p[0],16)
        except: continue
        syms.append((a,p[2],p[1]))
syms.sort(); A=[s[0] for s in syms]
def cont(va):
    i=bisect.bisect_right(A,va)-1
    if i<0: return None
    return syms[i], va-syms[i][0]

for name in ("el0_svc_naked","__arch_copy_to_user","__arch_copy_from_user","copy_page_to_iter","shmem_file_read_iter","__copy_to_user","do_core_ctl"):
    for a,n,t in syms:
        if n==name:
            print("%-24s %#x  off_from_image=%#x" % (n, a, a-KIMAGE)); break

S = 0x98000
print("\n=== S = %#x ===" % S)
for ip,c in IPS:
    u = ip - S
    r = cont(u)
    if r:
        (a,n,t),off = r
        print("  %016x count=%-5d -> %-34s +%#x [%s]" % (ip,c,n,off,t))
    else:
        print("  %016x count=%-5d -> ?" % (ip,c))
