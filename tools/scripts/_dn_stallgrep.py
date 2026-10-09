#!/usr/bin/env python3
import zipfile, glob, re
for p in sorted(glob.glob("/mnt/e/Library/Desktop/ghostlock/kp_*.gz")):
    try:
        z = zipfile.ZipFile(p)
        nm = "dumpstate_lastkmsg.lst" if "dumpstate_lastkmsg.lst" in z.namelist() else z.namelist()[0]
        L = z.read(nm).decode("utf-8","replace").splitlines()
    except Exception as e:
        continue
    hits = [l for l in L if re.search(r"sched_setattr|rt_mutex_adjust|sec_debug_save_context|hard LOCKUP|rcu_sched|rcu_preempt|watchdog.*bite|Watchdog.*bite", l)]
    if hits:
        print("==== %s (%d) ====" % (p.split('/')[-1], len(hits)))
        for l in hits[:8]:
            print("   ", l[:165])
