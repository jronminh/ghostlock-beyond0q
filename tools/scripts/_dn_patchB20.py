#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "root.c")
s = open(F, encoding="utf-8").read()

old = """int install_android_root(int fd) {
  root_uid_before = getuid();
  if (!spawn_root_child()) {
    pr_info("root spawn failed child=%d\\n", root_child_pid);
    return 0;
  }

  uintptr_t selinux_addr = data_addr(SELINUX_ENFORCING);
  pipe_phys_read_data(fd, selinux_addr, &selinux_before, sizeof(selinux_before));"""
new = """int install_android_root(int fd) {
  root_uid_before = getuid();
  /* configfs read BEFORE fork (baseline) */
  {
    uint64_t pre = pipe_read64(fd, data_addr(INIT_TASK_TASKS));
    pr_info("root: pre-fork cfg read=%016llx\\n", (unsigned long long)pre); fsync(1);
  }
  if (!spawn_root_child()) {
    pr_info("root spawn failed child=%d\\n", root_child_pid);
    return 0;
  }
  pr_info("root: after spawn (cfg read next)\\n"); fsync(1);

  uintptr_t selinux_addr = data_addr(SELINUX_ENFORCING);
  pipe_phys_read_data(fd, selinux_addr, &selinux_before, sizeof(selinux_before));
  pr_info("root: post-fork cfg read selinux=%02x\\n", selinux_before); fsync(1);"""
if s.count(old) != 1:
    print("FAIL1 %d" % s.count(old)); sys.exit(1)
s = s.replace(old, new)

old2 = """  init_tasks_prev = pipe_read64(fd, data_addr(INIT_TASK_TASKS) + 8);"""
new2 = """  init_tasks_prev = pipe_read64(fd, data_addr(INIT_TASK_TASKS) + 8);
  pr_info("root: init_tasks_prev=%016llx\\n", (unsigned long long)init_tasks_prev); fsync(1);"""
if s.count(old2) != 1:
    print("FAIL2 %d" % s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

old3 = """  if (found_task_tgid != (uint32_t)root_child_pid) {"""
new3 = """  pr_info("root: task cand pid=%u tgid=%u\\n", found_task_pid, found_task_tgid); fsync(1);
  if (found_task_tgid != (uint32_t)root_child_pid) {"""
if s.count(old3) != 1:
    print("FAIL3 %d" % s.count(old3)); sys.exit(1)
s = s.replace(old3, new3)

open(F, "w", encoding="utf-8").write(s)
print("ok")
