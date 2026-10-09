#!/usr/bin/env python3
"""_grep_dump.py <dump> <pattern> — grep member kernel log, in kèm ngữ cảnh."""
import zipfile, sys, re
p, pat = sys.argv[1], sys.argv[2]
ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 1
z = zipfile.ZipFile(p)
L = z.read("dumpstate_lastkmsg.lst").decode("utf-8", "replace").splitlines()
r = re.compile(pat)
hits = [i for i, l in enumerate(L) if r.search(l)]
print("hits:", len(hits))
seen = set()
for i in hits:
    for j in range(max(0, i - ctx), min(len(L), i + ctx + 1)):
        if j not in seen:
            seen.add(j)
            print("%6d %s" % (j, L[j][:165]))
