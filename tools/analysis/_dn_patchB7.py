#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "util.c")
s = open(F, encoding="utf-8").read()
old = "    binwrite_target = payload_base + 0x800;   /* outside the 0x319 fops table */\n"
new = ("    /* In-page scratch.  payload_base+0x800 == page_base-0x680, which is\n"
       "     * OUTSIDE this port's single 4 KB memfd page; keep the CFI test fully\n"
       "     * inside the page (payload_base+LOCK_OFF == page_base). */\n"
       "    binwrite_target = payload_base + LOCK_OFF + 0x700;\n")
if s.count(old) != 1:
    print("FAIL: %d occurrences" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
