#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "root.c")
s = open(F, encoding="utf-8").read()

old = """int spawn_root_child(void) {
  int prot = PROT_READ | PROT_WRITE;
  int flags = MAP_SHARED | MAP_ANONYMOUS;
  root_shared = SYSCHK(mmap(NULL, sizeof(*root_shared), prot, flags, -1, 0));
  memset(root_shared, 0, sizeof(*root_shared));
  SYSCHK(pipe(root_ready_pipe));

  root_child_pid = SYSCHK(fork());"""
new = """int spawn_root_child(void) {
  int prot = PROT_READ | PROT_WRITE;
  int flags = MAP_SHARED | MAP_ANONYMOUS;
  pr_info("spawn: mmap...\\n"); fsync(1);
  root_shared = SYSCHK(mmap(NULL, sizeof(*root_shared), prot, flags, -1, 0));
  memset(root_shared, 0, sizeof(*root_shared));
  pr_info("spawn: pipe...\\n"); fsync(1);
  SYSCHK(pipe(root_ready_pipe));

  pr_info("spawn: fork...\\n"); fsync(1);
  root_child_pid = SYSCHK(fork());
  pr_info("spawn: fork ret=%d\\n", root_child_pid); fsync(1);"""
if s.count(old) != 1:
    print("FAIL1 %d" % s.count(old)); sys.exit(1)
s = s.replace(old, new)

old2 = """    prctl(PR_SET_NAME, "ll_root_child");
    char ready = 1;
    SYSCHK(write(root_ready_pipe[1], &ready, sizeof(ready)));"""
new2 = """    prctl(PR_SET_NAME, "ll_root_child");
    char ready = 1;
    {
      ssize_t wr = write(root_ready_pipe[1], &ready, sizeof(ready));
      (void)wr;
    }"""
if s.count(old2) != 1:
    print("FAIL2 %d" % s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

old3 = """  close(root_ready_pipe[1]);

  char ready;
  ssize_t got = read(root_ready_pipe[0], &ready, sizeof(ready));
  return got == (ssize_t)sizeof(ready);"""
new3 = """  close(root_ready_pipe[1]);

  char ready = 0;
  pr_info("spawn: parent wait ready...\\n"); fsync(1);
  ssize_t got = read(root_ready_pipe[0], &ready, sizeof(ready));
  pr_info("spawn: parent got=%zd\\n", got); fsync(1);
  return got == (ssize_t)sizeof(ready);"""
if s.count(old3) != 1:
    print("FAIL3 %d" % s.count(old3)); sys.exit(1)
s = s.replace(old3, new3)

open(F, "w", encoding="utf-8").write(s)
print("ok")
