#!/usr/bin/env python3
"""patch_only_fops.py

ONLY_FOPS=1 : dừng NGAY sau pha mode-4 (fops redirect), không chạy các pha W1/W2
(hiện vẫn crash vì lý do riêng).  Dùng để có một lệnh chạy SẠCH làm chuẩn kiểm
chứng redirect, và để không tốn reboot.
"""
M = "/root/ghostlock/ghostlock-oneplus/src/core/main.c"
s = open(M).read()
old = """    do_one_write(data_addr(ASHMEM_MISC_FOPS), "fops redirect", 4);
    TIMER("fops redirect done");
    selinux_ok = check_selinux_off();
  }
"""
new = """    do_one_write(data_addr(ASHMEM_MISC_FOPS), "fops redirect", 4);
    TIMER("fops redirect done");
    selinux_ok = check_selinux_off();
  }

  if (env_flag("ONLY_FOPS", 0)) {
    /* Diagnostic stop: the W1/W2 phases still crash for unrelated reasons
     * (see BAN_GIAO §19.3); with ONLY_FOPS=1 a run is clean and verifies the
     * mode-4 fops redirect without tripping them. */
    pr_success("ONLY_FOPS: stop after fops redirect (selinux_off=%d)\\n",
               selinux_ok);
    fsync(1);
    return 0;
  }
"""
assert s.count(old) == 1, ("only_fops", s.count(old))
s = s.replace(old, new, 1)
open(M, "w").write(s)
print("main.c: ONLY_FOPS=1 stop after mode-4")
