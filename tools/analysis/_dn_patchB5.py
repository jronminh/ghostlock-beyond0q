#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "fops.c")
s = open(F, encoding="utf-8").read()
old = """  if (!env_flag("SKIP_UMH", 0)) {
    if (install_umh_root(fd)) return 1;
  }
  return install_android_root(fd);
"""
new = """  if (!env_flag("SKIP_UMH", 0)) {
    if (install_umh_root(fd)) return 1;
  }
  if (env_flag("SKIP_CRED", 0)) return 0;
  return install_android_root(fd);
"""
if s.count(old) != 1:
    print("FAIL: %d occurrences" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
