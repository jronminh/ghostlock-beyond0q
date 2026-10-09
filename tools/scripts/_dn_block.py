#!/usr/bin/env python3
import zipfile, sys
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp_B7.gz")
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
c = int(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv)>2 else 90
for i in range(c, min(len(L), c+n)):
    print("%6d %s" % (i, L[i][:170]))
