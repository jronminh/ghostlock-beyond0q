#!/usr/bin/env python3
"""_scan78.py — tìm trace CPU bị kẹt trong dump 78 (hàm thật, không phải idle)."""
import zipfile, re, sys
p = sys.argv[1] if len(sys.argv) > 1 else "kp_dumpstate_lastkmsg_78_20260622_074142_KP.log.gz"
z = zipfile.ZipFile(p)
t = z.read("dumpstate_lastkmsg.lst").decode("utf-8", "replace")
lines = t.splitlines()
pat = re.compile(r"rt_mutex|sched_setattr|rb_erase|____rb_erase|SyS_futex|do_futex|adjust_prio")
hit = [i for i, l in enumerate(lines) if pat.search(l)]
print("members:", z.namelist()[:2], "lines:", len(lines), "matches:", len(hit))
for i in hit[:12]:
    print("  %5d %s" % (i, lines[i][:150]))
if hit:
    print("---- quanh match CUOI ----")
    for i in range(max(0, hit[-1] - 25), min(len(lines), hit[-1] + 4)):
        print("  %5d %s" % (i, lines[i][:150]))
