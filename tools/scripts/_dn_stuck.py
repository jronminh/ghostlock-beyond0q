#!/usr/bin/env python3
import zipfile, sys, re
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/%s.gz" % sys.argv[1])
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
print("lines", len(L))
# find all Call trace blocks; classify
idle = ("lpm_cpuidle_enter", "cpu_do_idle", "arch_cpu_idle", "default_idle", "cpuidle_enter")
blocks = []
i = 0
while i < len(L):
    if "Call trace" in L[i] or re.search(r"pc : ", L[i]):
        # gather ~12 lines
        blk = L[i:i+14]
        blocks.append((i, blk))
        i += 14
    else:
        i += 1
def is_idle(blk):
    return any(any(k in l for k in idle) for l in blk)
print("total blocks", len(blocks))
print("=== NON-idle blocks (the interesting ones) ===")
for off, blk in blocks:
    if not is_idle(blk):
        print("---- block at %d ----" % off)
        for l in blk:
            print("   ", l[:170])
print("=== last 20 lines ===")
for l in L[-20:]:
    print("   ", l[:170])
