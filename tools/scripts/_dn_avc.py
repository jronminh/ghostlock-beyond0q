#!/usr/bin/env python3
import zipfile, re
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp_B7.gz")
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
print("=== avc denied lines ===")
for i,l in enumerate(L):
    if "avc:" in l and ("denied" in l):
        if "kernel" in l or "exec" in l or "shell_data" in l or "a/e" in l or "ghostlock" in l:
            print("%6d %s" % (i, l[:180]))
print("=== lines mentioning /data/local/tmp/a or 'e --umh' or kernel exec ===")
for i,l in enumerate(L):
    if ("tmp/a" in l) or ("--umh" in l) or ("u:r:kernel" in l):
        print("%6d %s" % (i, l[:180]))
