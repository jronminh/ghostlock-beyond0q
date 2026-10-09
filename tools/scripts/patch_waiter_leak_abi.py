#!/usr/bin/env python3
"""patch_waiter_leak_abi.py

Sample aarch64 có `abi = PERF_SAMPLE_REGS_ABI_64 = 2` (không phải 1 — 1 là ABI_32).
Bản trước lọc abi==1 nên accepted=0.  Sửa: nhận abi==2, log histogram abi để chẩn đoán.
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

old = """      if (abi == 1) {
        uint64_t sp = ((uint64_t *)p)[31];"""
new = """      if (abi < 4) wl_abi_hist[abi]++;
      if (abi == 2) {                       /* PERF_SAMPLE_REGS_ABI_64 */
        uint64_t sp = ((uint64_t *)p)[31];"""
assert u.count(old) == 1, ("abi check", u.count(old))
u = u.replace(old, new, 1)

old = """static uint64_t wl_lo_hist[256];                 /* SP & 0x3fff histogram */"""
new = """static uint64_t wl_lo_hist[256];                 /* SP & 0x3fff histogram */
static uint64_t wl_abi_hist[4];                  /* abi histogram */"""
assert u.count(old) == 1, ("hist decl", u.count(old))
u = u.replace(old, new, 1)

old = """          wl_samples, wl_insock, wl_nc, (uintptr_t)best, bestn, wl_ring_lost,
          (size_t)wl_lo_mask);"""
new = """          wl_samples, wl_insock, wl_nc, (uintptr_t)best, bestn, wl_ring_lost,
          (size_t)wl_lo_mask);
  pr_info("  abi hist: none=%d a32=%d a64=%d x=%d\\n",
          (int)wl_abi_hist[0], (int)wl_abi_hist[1], (int)wl_abi_hist[2],
          (int)wl_abi_hist[3]);"""
assert u.count(old) == 1, ("abi log", u.count(old))
u = u.replace(old, new, 1)
open(U, "w").write(u)
print("util.c: accept abi==2 (+ abi histogram)")
