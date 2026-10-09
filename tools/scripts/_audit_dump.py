import struct, zipfile, re
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
d=open(IMG,"rb").read()
def find(s,n=12):
    r=[];s0=0
    while True:
        i=d.find(s,s0)
        if i<0: break
        r.append(i);s0=i+1
    return r[:n]
print("'swapper' offsets:", [hex(x) for x in find(b"swapper")])
for comm in (0x858,0x910,0xa8):
    for s in find(b"swapper",4):
        print("  comm_off=%#x -> init_task img off=%#x (kallsyms 0x29a9780)"%(comm,s-comm))
# dump 85: SX vs SY stalls
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp85.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
print("\n--- dump85: ghostlock + rcu/watchdog lines ---")
for i,l in enumerate(L):
    if re.search(r"ghostlockS[XZ]|rcu_\w+ self-detected|watchdog: BUG|sec_debug_pm_restart|Unable to handle|Kernel Offset", l):
        print("%6d %s" % (i, l.split("]")[-1].strip()[:120]))
