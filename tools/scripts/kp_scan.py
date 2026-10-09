#!/usr/bin/env python3
"""kp_scan.py <dump.gz> [...]  — doc /data/log/dumpstate_lastkmsg_*.log.gz (ZIP).

Chỉ quét member kernel log (`dumpstate_lastkmsg.lst`), KHÔNG in member HTML
(store_extra_info.lst rất ồn).  In:
  - mọi dòng chứa 'ghostlockQ' (+/-2 dòng quanh dòng đầu tiên)
  - các dòng kết thúc/khóa máy: rebooting / Call trace / watchdog / lockup / BUG / stall
Dùng: wsl -e bash -lc 'cd /mnt/e/Library/Desktop/ghostlock && python3 kp_scan.py kp_xxx.gz'
"""
import sys, zipfile, re

KMSG_MEMBER = "dumpstate_lastkmsg.lst"
pat_proc = re.compile(r"ghostlock")
pat_end = re.compile(r"rebooting|Call trace|watchdog|lockup|BUG:|stall|Internal error|Unable to handle|pc :")

for p in sys.argv[1:]:
    print("===================== %s" % p)
    try:
        z = zipfile.ZipFile(p)
    except Exception as e:
        print("  !! not zip:", e); continue
    name = KMSG_MEMBER if KMSG_MEMBER in z.namelist() else z.namelist()[0]
    txt = z.read(name).decode("utf-8", "replace")
    lines = txt.splitlines()
    print("  member=%s lines=%d" % (name, len(lines)))
    hits = [i for i, l in enumerate(lines) if pat_proc.search(l)]
    if hits:
        lo = max(0, hits[0] - 2)
        for i in range(lo, min(len(lines), hits[0] + 6)):
            print("   P %5d: %s" % (i, lines[i]))
        print("   ... (%d dòng có 'ghostlock') ..." % len(hits))
        for i in hits[-4:]:
            print("   P %5d: %s" % (i, lines[i]))
    else:
        print("   (không có dòng nào chứa 'ghostlock')")
    ends = [i for i, l in enumerate(lines) if pat_end.search(l)]
    print("  -- dòng sự kiện cuối (%d) --" % len(ends))
    for i in ends[-12:]:
        print("   E %5d: %s" % (i, lines[i]))
