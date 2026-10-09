#!/usr/bin/env python3
"""_last.py <dump> [who] — in block register/trace của (các) crash cuối cùng."""
import zipfile, re, sys
p = sys.argv[1]
who = sys.argv[2] if len(sys.argv) > 2 else "ghostlockQ"
z = zipfile.ZipFile(p)
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8", "replace").splitlines()
idx = [i for i, l in enumerate(L)
       if who in l and ("Unable to handle" in l or "Call trace" in l)]
print("blocks:", len(idx))
sel = sys.argv[3:] if len(sys.argv) > 3 else None
for c in idx[-3:]:
    print("===== block at line %d" % c)
    for i in range(max(0, c - 24), min(len(L), c + 14)):
        s = L[i]
        if re.search(r"x\d+ :|pc :|lr :|Process |Unable to handle|Call trace|end trace|Code:", s):
            print("  %5d %s" % (i, s[:150]))
