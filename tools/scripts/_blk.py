#!/usr/bin/env python3
"""_blk.py <dump> <from> <to> — in raw các dòng [from,to) của member kernel log."""
import zipfile, sys
p, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
z = zipfile.ZipFile(p)
lines = z.read("dumpstate_lastkmsg.lst").decode("utf-8", "replace").splitlines()
for i in range(a, min(b, len(lines))):
    print("%5d %s" % (i, lines[i][:170]))
