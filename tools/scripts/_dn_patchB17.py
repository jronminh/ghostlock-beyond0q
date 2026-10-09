#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "root.c")
s = open(F, encoding="utf-8").read()
old = """  pr_info("root task=%016llx pid=%u tgid=%u comm=%s real_cred=%016llx cred=%016llx\\n",
          (unsigned long long)current_task_addr, found_task_pid, found_task_tgid,
          found_task_comm, (unsigned long long)current_real_cred_addr,
          (unsigned long long)current_cred_addr);"""
new = """  pr_info("root self=%d child=%d task=%016llx pid=%u tgid=%u comm=%s real_cred=%016llx cred=%016llx\\n",
          getpid(), root_child_pid, (unsigned long long)current_task_addr,
          found_task_pid, found_task_tgid, found_task_comm,
          (unsigned long long)current_real_cred_addr,
          (unsigned long long)current_cred_addr);
  for (uintptr_t off = 0x828; off <= 0x870; off += 8)
    pr_info("root task[%03zx]=%016llx", (size_t)off,
            (unsigned long long)pipe_read64(fd, current_task_addr + off));"""
if s.count(old) != 1:
    print("FAIL: %d" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
