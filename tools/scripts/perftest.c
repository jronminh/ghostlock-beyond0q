/* perftest: can perf REGS_INTR sampling during sendmsg() catch a kernel heap
 * (direct-map) pointer?  Non-destructive. */
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
#include <sys/socket.h>
#include <linux/perf_event.h>

static char pay[0x10000];

int main(int argc, char **argv) {
  setvbuf(stdout, NULL, _IONBF, 0);
  long per = (argc > 1) ? atol(argv[1]) : 1000;

  int sv[2];
  if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) < 0) { printf("socketpair errno=%d\n", errno); return 1; }
  memset(pay, 0x41, sizeof pay);

  struct perf_event_attr pe;
  memset(&pe, 0, sizeof pe);
  pe.type = PERF_TYPE_SOFTWARE;
  pe.size = sizeof pe;
  pe.config = PERF_COUNT_SW_CPU_CLOCK;
  pe.sample_period = (uint64_t)per;
  pe.sample_type = PERF_SAMPLE_IP | PERF_SAMPLE_REGS_INTR;
  pe.sample_regs_intr = (1ULL << 32) - 1;
  pe.disabled = 1;
  pe.exclude_user = 1;
  pe.exclude_hv = 1;
  pe.exclude_idle = 1;

  int fd = (int)syscall(__NR_perf_event_open, &pe, 0, -1, -1, 0);
  if (fd < 0) { printf("perf_event_open errno=%d\n", errno); return 1; }
  size_t msz = 4096 * 33;
  uint8_t *buf = mmap(NULL, msz, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (buf == MAP_FAILED) { printf("mmap errno=%d\n", errno); return 1; }

  ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
  long sends = 0;
  for (long i = 0; i < 400000; i++) {
    struct iovec iov = { pay, sizeof pay };
    struct msghdr m; memset(&m, 0, sizeof m); m.msg_iov = &iov; m.msg_iovlen = 1;
    ssize_t s = sendmsg(sv[0], &m, MSG_DONTWAIT);
    if (s > 0) sends++;
    char tmp[65536];
    while (recv(sv[1], tmp, sizeof tmp, MSG_DONTWAIT) > 0) {}
  }
  ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);

  struct perf_event_mmap_page *hdr = (void *)buf;
  uint64_t head = hdr->data_head;
  __sync_synchronize();
  char *base = (char *)buf + 4096;
  size_t dsz = 4096 * 32;
  uint64_t pos = hdr->data_tail;

  static uint64_t cands[16384];
  static int counts[16384];
  int nc = 0;
  long nreg = 0, ntext = 0, nvm = 0, ndm = 0, nother = 0, nsamp = 0;
  while (pos < head) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    if (ev->type == PERF_RECORD_SAMPLE) {
      nsamp++;
      char *p = (char *)ev + sizeof(*ev);
      p += 8; /* ip */
      uint64_t abi = *(uint64_t *)p; p += 8;
      if (abi == 1 || abi == 2) {
        uint64_t *regs = (uint64_t *)p;
        for (int i = 0; i < 32; i++) {
          uint64_t v = regs[i];
          if (v >= 0xffffff8000000000ULL && v < 0xfffffffe00000000ULL) {
            nreg++;
            if (v < 0xffffffbf00000000ULL) ntext++;
            else if (v < 0xffffffc000000000ULL) nvm++;
            else if (v < 0xffffffff00000000ULL) ndm++;
            else nother++;
            int f = -1;
            for (int k = 0; k < nc; k++) if (cands[k] == v) { f = k; break; }
            if (f < 0 && nc < 16384) { cands[nc] = v; counts[nc] = 1; nc++; }
            else if (f >= 0) counts[f]++;
          }
        }
      }
    }
    pos += ev->size;
  }
  printf("sends=%ld samples=%ld kernel_regs=%ld text=%ld vmemmap=%ld directmap=%ld other=%ld distinct=%d\n",
         sends, nsamp, nreg, ntext, nvm, ndm, nother, nc);
  for (int r = 0; r < 25; r++) {
    int bi = -1;
    for (int k = 0; k < nc; k++) { if (counts[k] < 0) continue; if (bi < 0 || counts[k] > counts[bi]) bi = k; }
    if (bi < 0) break;
    const char *cls = (cands[bi] >= 0xffffffc000000000ULL) ? "DIREMAP" :
                      (cands[bi] >= 0xffffffbf00000000ULL) ? "VMEM" : "TEXT/VIRT";
    printf("  %016llx count=%d %s\n", (unsigned long long)cands[bi], counts[bi], cls);
    counts[bi] = -1;
  }
  return 0;
}
