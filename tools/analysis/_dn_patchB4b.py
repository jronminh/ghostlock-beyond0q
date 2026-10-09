#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()
old = """  int32_t umh_retval = (int32_t)umh_read32(
    fd, fake_work_addr + offsetof(struct umh_subprocess_info, retval));

  pr_info("umh: result wake=%d complete=%u retval=%d\\n",
          wake_ok, complete_done, umh_retval);
"""
new = """  int32_t umh_retval = (int32_t)umh_read32(
    fd, fake_work_addr + offsetof(struct umh_subprocess_info, retval));

  pr_info("umh: post worklist=%016llx entry=%016llx work_data=%016llx "
          "nr_active=%u retval=%d\\n",
          (unsigned long long)umh_read64(fd, worklist),
          (unsigned long long)umh_read64(fd, worklist + sizeof(uint64_t)),
          (unsigned long long)umh_read64(fd, fake_work_addr + WORK_DATA_OFF),
          umh_read32(fd, pwq + PWQ_NR_ACTIVE_OFF), umh_retval);
  fsync(1);

  pr_info("umh: result wake=%d complete=%u retval=%d\\n",
          wake_ok, complete_done, umh_retval);
"""
if s.count(old) != 1:
    print("FAIL: %d occurrences" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
