#!/usr/bin/env python3
import zipfile, re
z = zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp_B7.gz")
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
pats = ["defex", "DEFEX", "Defex", "rkp", "RKP", "KDP", "kdp",
        "umh", "UMH", "usermodehelper", "kernel_execve", "call_usermodehelper",
        "shell_data_file"]
for pat in pats:
    hits = [i for i,l in enumerate(L) if pat in l]
    print("== %-20s hits=%d" % (pat, len(hits)))
    for i in hits[:6]:
        print("   %6d %s" % (i, L[i][:170]))
