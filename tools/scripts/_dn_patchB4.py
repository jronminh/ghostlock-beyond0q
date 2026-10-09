#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")

def patch(path, old, new):
    p = os.path.join(CORE, path)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        print("FAIL %s: %d occurrences of %r" % (path, s.count(old), old[:120])); sys.exit(1)
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok  %s" % path)

F = "umh_root.c"

# 1. wake via actual tty data (tty_schedule_flip -> queue_work(system_unbound_wq))
patch(F,
"""  int master_ok = close(master_fd) == 0;
  int slave_ok = close(slave_fd) == 0;
  return master_ok && slave_ok;
}""",
"""  /* Merely opening a pty does not push the tty buffer work.  Write a byte so
   * tty_schedule_flip() runs queue_work(system_unbound_wq, &port->buf.work):
   * that wakes an idle worker of the same pool, and the worker then drains our
   * fake work item sitting at the head of the pool worklist. */
  char b = 'x';
  ssize_t wm = write(master_fd, &b, 1);
  ssize_t ws = write(slave_fd, &b, 1);
  /* leave the pty open briefly so the queued work is not cancelled by close */
  usleep(3000);
  int master_ok = close(master_fd) == 0;
  int slave_ok = close(slave_fd) == 0;
  return wm == 1 || ws == 1 || (master_ok && slave_ok);
}""")

# 2. post-wake diagnostics: did the worker consume our entry / touch work->data?
patch(F,
"""  int32_t umh_retval = (int32_t)umh_read32(
      fd, fake_work_addr + offsetof(struct umh_subprocess_info, retval));

  pr_info("umh: result wake=%d complete=%u retval=%d\\n",
          wake_ok, complete_done, umh_retval);""",
"""  int32_t umh_retval = (int32_t)umh_read32(
      fd, fake_work_addr + offsetof(struct umh_subprocess_info, retval));

  pr_info("umh: post worklist=%016llx entry=%016llx work_data=%016llx "
          "nr_active=%u retval=%d\\n",
          (unsigned long long)umh_read64(fd, worklist),
          (unsigned long long)umh_read64(fd, worklist + sizeof(uint64_t)),
          (unsigned long long)umh_read64(fd, fake_work_addr + WORK_DATA_OFF),
          umh_read32(fd, pwq + PWQ_NR_ACTIVE_OFF), umh_retval);
  fsync(1);

  pr_info("umh: result wake=%d complete=%u retval=%d\\n",
          wake_ok, complete_done, umh_retval);""")

print("done")
