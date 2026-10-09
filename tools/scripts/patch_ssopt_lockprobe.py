#!/usr/bin/env python3
"""patch_ssopt_lockprobe.py

Phép thử DỨT KHOÁT "paint có tới stack không", không thể treo:
  SSOPT_LOCKPROBE=1 -> paint len=0x50: buf[0x40]=task, buf[0x48]=0x1a2b00000048,
  các slot khác = 0 (tree_entry = 0 nên rb_erase luôn đi nhánh an toàn nếu tới).
  Nếu paint TỚI  : walk dừng ngay [5] raw_spin_trylock(lock) với lock = 0x1a2b00000048
                   -> fault non-canonical -> KP ngay, x24 = 0x1a2b00000048
  Nếu paint KHÔNG: lock = 0 (do memset để lại) -> fault VA=0 -> KP, x24 = 0
  Cả hai đều là KP nhanh + đọc được x24  => không còn ca "treo không có dump".
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

old = """    if (env_flag("SSOPT_SCAN", 0)) {"""
new = """    if (env_flag("SSOPT_LOCKPROBE", 0)) {
      /* Deterministic "did the paint reach the stack?" probe: lock = a
       * non-canonical marker so chain[5] raw_spin_trylock() faults at once
       * (KP in milliseconds, never a hang), and x24 reveals whether the copy
       * landed (0x1a2b00000048) or stayed zeroed by the memset (0). */
      put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                      : text_addr(INIT_TASK));
      put64(buf, 0x48, 0x1a2b00000048ULL);
    } else if (env_flag("SSOPT_SCAN", 0)) {"""
assert s.count(old) == 1, ("lockprobe", s.count(old))
s = s.replace(old, new, 1)

old = """    socklen_t paint_len = env_flag("SSOPT_BASELINE", 0) ? 0x50 : 0x60;"""
new = """    socklen_t paint_len = (env_flag("SSOPT_BASELINE", 0) ||
                           env_flag("SSOPT_LOCKPROBE", 0)) ? 0x50 : 0x60;"""
assert s.count(old) == 1, ("len", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: SSOPT_LOCKPROBE (deterministic paint-lands probe)")
