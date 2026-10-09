#!/usr/bin/env python3
import zipfile, sys
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/%s.gz" % sys.argv[1])
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
key = ["Unable to handle", "Internal error", "Kernel panic", "watchdog bite", "Watchdog bite", "hard LOCKUP", "RCU Stall", "stall"]
idx = [i for i,l in enumerate(L) if any(k in l for k in key)]
print("lines", len(L), "events", idx[-8:])
if idx:
    c = idx[-1]
    # walk back to the start of this fault block
    start = c
    for j in range(c, max(0,c-6), -1):
        if "Unable to handle" in L[j] or "Internal error" in L[j] or "LOCKUP" in L[j] or "panic" in L[j]:
            start = j
    for i in range(max(0,start-2), min(len(L), start+42)):
        print("%6d %s" % (i, L[i][:175]))
        if "end trace" in L[i]: break
