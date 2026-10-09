/* slubtest7: free test slab (empty, frozen), then free WHOLE other slabs and
 * watch for discards.  Non-destructive. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <sched.h>
#include <string.h>

#define MAXK 3000
#define MAXST 60

static long mm_slabs(void) {
  FILE *f = fopen("/proc/slabinfo", "r"); if (!f) return -1; char line[512]; long total = -1;
  while (fgets(line, sizeof line, f)) {
    if (strncmp(line, "mm_struct ", 10)) continue;
    char *p = strstr(line, "slabdata");
    if (p) { long a = -1; sscanf(p + 8, "%ld %ld", &a, &total); }
    break;
  }
  fclose(f); return total;
}
static void pin0(void) { cpu_set_t s; CPU_ZERO(&s); CPU_SET(0, &s); sched_setaffinity(0, sizeof s, &s); }
static pid_t kids[MAXK]; static int mfds[MAXK]; static int n;
static void add_kid(void) {
  pid_t p = fork(); if (p == 0) { pin0(); for (;;) pause(); }
  kids[n] = p; char path[64]; snprintf(path, sizeof path, "/proc/%d/mem", p);
  mfds[n] = (p > 0) ? open(path, O_RDONLY) : -1; n++;
}
static void free_kid(int i) {
  if (i < 0 || i >= n) return;
  if (mfds[i] > 0) { close(mfds[i]); mfds[i] = -1; }
  if (kids[i] > 0) { kill(kids[i], SIGKILL); waitpid(kids[i], NULL, 0); kids[i] = 0; }
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  struct rlimit r; getrlimit(RLIMIT_NPROC, &r); r.rlim_cur = r.rlim_max; setrlimit(RLIMIT_NPROC, &r);
  pin0();
  int starts[MAXST]; int ns = 0; long prev = mm_slabs();
  while (n < MAXK - 80 && ns < MAXST) { add_kid(); long s = mm_slabs(); if (s > prev) { starts[ns++] = n - 1; prev = s; } }
  for (int j = 0; j < 80; j++) add_kid();
  long full = mm_slabs();
  printf("allocated n=%d slabs=%ld\n", n, full);

  /* test slab -> empty+frozen */
  for (int k = starts[0]; k < starts[0] + 36; k++) free_kid(k);
  printf("after free test slab: slabs=%ld\n", mm_slabs());

  long cur = mm_slabs();
  for (int c = 1; c < ns; c++) {
    for (int k = starts[c]; k < starts[c] + 36; k++) free_kid(k);   /* whole slab */
    long s = mm_slabs();
    if (s != cur) { printf("  after freeing whole slab %d: slabs=%ld (DROP %ld)\n", c, s, cur - s); cur = s; }
    if (c >= 40) break;
  }
  printf("after whole-slab churn: slabs=%ld\n", mm_slabs());
  for (int i = 0; i < n; i++) free_kid(i);
  printf("cleanup slabs=%ld\n", mm_slabs());
  return 0;
}
