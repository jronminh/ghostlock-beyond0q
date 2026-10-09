#!/usr/bin/env python3
import zipfile, sys
p = sys.argv[1]
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/%s.gz" % p)
names = z.namelist()
mem = "dumpstate_lastkmsg.lst" if "dumpstate_lastkmsg.lst" in names else names[0]
L = z.read(mem).decode("utf-8","replace").splitlines()
print("member", mem, "lines", len(L))
idx = [i for i,l in enumerate(L) if "Unable to handle" in l or "Internal error" in l or "Kernel panic" in l or "watchdog" in l.lower()]
print("event lines:", idx[-6:])
if idx:
    c = idx[0]
    for i in range(max(0,c-2), min(len(L), c+34)):
        print("%6d %s" % (i, L[i][:175]))
        if "end trace" in L[i]: break
