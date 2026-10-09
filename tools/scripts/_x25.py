#!/usr/bin/env python3
"""_x25.py — in block register (x29..x0) quanh trace của một tiến trình trong dump."""
import zipfile, re, sys
p, who = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(p)
t = z.read("dumpstate_lastkmsg.lst").decode("utf-8", "replace")
lines = t.splitlines()
idx = [i for i, l in enumerate(lines) if who in l and "Call trace" in l]
print("crashes for %s: %d" % (who, len(idx)))
for c in idx[-1:]:
    print("--- block quanh %d ---" % c)
    for i in range(max(0, c - 40), min(len(lines), c + 3)):
        s = lines[i]
        if re.search(r"x\d+ :|pc :|lr :|sp :|Call trace|Stack|Process", s):
            print("  %5d %s" % (i, s[:160]))
