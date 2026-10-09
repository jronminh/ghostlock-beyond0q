#!/usr/bin/env python3
"""patch_ssopt_fsync.py

Log phải sống qua panic: ghi ra file + fsync (panic làm mất page cache, nên
_IONBF không đủ).  Thêm fsync(1) ngay sau các dòng chẩn đoán quan trọng trong
route setsockopt.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

old = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf);"""
new = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf);
    fsync(1);   /* panic loses the page cache: force the log to disk */"""
assert s.count(old) == 1, ("fsync pre", s.count(old))
s = s.replace(old, new, 1)

old = """              (uintptr_t)ssopt_page_readback(SSOPT_PG(SCRATCH_OFF) + 0x40));
    }"""
new = """              (uintptr_t)ssopt_page_readback(SSOPT_PG(SCRATCH_OFF) + 0x40));
      fsync(1);
    }"""
assert s.count(old) == 1, ("fsync peek", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: fsync(1) after pre-paint and peek diagnostics")
