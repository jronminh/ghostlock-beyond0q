#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")

def patch(path, old, new, cnt=1):
    p = os.path.join(CORE, path)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != cnt:
        print("FAIL %s: %d occurrences (want %d) of %r" % (path, s.count(old), cnt, old[:100])); sys.exit(1)
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok  %s" % path)

# selinux_enforcing (the int read by enforcing_enabled()) is at 0x02DC8CE8, not
# 0x02DC8CC8 (which is the start of struct selinux_state).
patch("target.h",
      "#define SELINUX_ENFORCING_OFF  0x02DC8CC8ULL\n",
      "#define SELINUX_ENFORCING_OFF  0x02DC8CE8ULL  /* global int selinux_enforcing (enforcing_enabled() reads this), NOT selinux_state@0x2DC8CC8 */\n")

patch("../devices/beyond0q/offsets.h",
      "  .off_selinux_enforcing = 0x02DC8CC8ULL,\n",
      "  .off_selinux_enforcing = 0x02DC8CE8ULL,  /* global int selinux_enforcing */\n")

# verify the write actually flipped /sys/fs/selinux/enforce
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()
old = """  pr_info("umh: step1 selinux write ok\\n");
  fsync(1);
"""
new = """  { int ef = open("/sys/fs/selinux/enforce", O_RDONLY); char eb[8] = {0};
    if (ef >= 0) { ssize_t rn = read(ef, eb, sizeof(eb) - 1); (void)rn; close(ef); }
    pr_info("umh: step1 selinux write ok; /sys/fs/selinux/enforce='%s'\\n", eb);
    fsync(1); }
"""
if s.count(old) != 1:
    print("FAIL umh_root verify: %d" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok  umh_root.c verify")
print("done")
