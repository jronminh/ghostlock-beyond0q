#!/usr/bin/env python3
import zipfile
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp_B14.gz")
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
idx = [i for i,l in enumerate(L) if "Unable to handle" in l or "Internal error" in l]
print("fault lines:", idx)
for c in idx:
    for i in range(max(0,c-2), min(len(L), c+40)):
        print("%6d %s" % (i, L[i][:175]))
        if "end trace" in L[i]:
            break
