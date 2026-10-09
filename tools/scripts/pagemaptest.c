/* pagemaptest: does /proc/self/pagemap expose the PFN (unprivileged) for a
 * MAP_SHARED memfd page?  Non-destructive. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <linux/memfd.h>

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  int fd = syscall(__NR_memfd_create, "x", 0);
  if (fd < 0) { printf("memfd errno=%d\n", errno); return 1; }
  if (ftruncate(fd, 4096) < 0) { printf("ftruncate errno=%d\n", errno); return 1; }
  char w[4096]; memset(w, 0x41, sizeof w);
  if (pwrite(fd, w, sizeof w, 0) != 4096) { printf("pwrite errno=%d\n", errno); return 1; }
  char *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (p == MAP_FAILED) { printf("mmap errno=%d\n", errno); return 1; }
  p[0] = 0x42; p[4095] = 0x43;   /* fault it in */
  uint64_t va = (uint64_t)p;
  uint64_t idx = (va >> 12) * 8;
  int pfd = open("/proc/self/pagemap", O_RDONLY);
  if (pfd < 0) { printf("open pagemap errno=%d\n", errno); return 1; }
  uint64_t ent = 0;
  if (pread(pfd, &ent, 8, (off_t)idx) != 8) { printf("pread pagemap errno=%d\n", errno); return 1; }
  close(pfd);
  uint64_t pfn = ent & ((1ULL << 55) - 1);
  printf("va=%016llx entry=%016llx present=%llu pfn=%llu\n",
         (unsigned long long)va, (unsigned long long)ent,
         (unsigned long long)(ent >> 63), (unsigned long long)pfn);
  if (pfn) {
    uint64_t phys = pfn << 12;
    printf("phys=%016llx  directmap(phys_offset=0x80000000)=%016llx\n",
           (unsigned long long)phys,
           (unsigned long long)(0xffffffc000000000ULL + (phys - 0x80000000ULL)));
  } else {
    printf("PFN zeroed (restricted)\n");
  }
  return 0;
}
