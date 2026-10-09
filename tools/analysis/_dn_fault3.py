#!/usr/bin/env python3
import zipfile, sys, re
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/%s.gz" % sys.argv[1])
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
print("lines", len(L))
pat = re.compile(r"Unable to handle|Internal error|Kernel panic|ghostlockB18|Hardware name|pc : |Call trace")
hits = [i for i,l in enumerate(L) if pat.search(l)]
print("hits", len(hits))
# show the tail 3 blocks of ghostlockB18 + any fault
fault = [i for i,l in enumerate(L) if "Unable to handle" in l or "Internal error" in l or "Kernel panic" in l]
print("faults", fault[-6:])
if fault:
    c = fault[-1]
    for i in range(max(0,c-2), min(len(L), c+40)):
        print("%6d %s" % (i, L[i][:175]))
        if "end trace" in L[i]: break
else:
    g = [i for i,l in enumerate(L) if "ghostlockB18" in l]
    print("ghostlockB18 lines", g[-10:])
    for i in g[-3:]:
        print("%6d %s" % (i, L[i][:175]))
