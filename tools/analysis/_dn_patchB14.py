#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "main.c")
s = open(F, encoding="utf-8").read()
old = "  if (!selinux_ok && umh_available) {\n"
new = "  if ((!selinux_ok || env_flag(\"FORCE_REDIRECT\", 0)) && umh_available) {\n"
if s.count(old) != 1:
    print("FAIL: %d" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
