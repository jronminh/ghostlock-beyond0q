/* slubtest3: identify real mm_struct slab boundaries by watching mm_slabs
 * grow, then test whether freeing a whole slab (with/without churn) discards
 * it.  Non-destructive. */
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

#define MAXK 2200
#define MAXST 22

static long mm_field(int which) {          /* 1=active, 2=total objects, ... */
  FILE *f = fopen("/proc/slabinfo", "r");
  if (!f) return -1;
  char line[512]; long v = -1;
  while (fgets(line, sizeof line, f)) {
    if (strncmp(line, "mm_struct ", 10)) continue;
    long a = 0, o = 0, sz = 0, ops = 0, pps = 0;
    sscanf(line + 10, "%ld %ld %ld %ld %ld", &a, &o, &sz, &ops, &pps);
    v = (which == 1) ? a : o;
    break;
  }
  fclose(f); return v;
}
static long mm_slabs(void) {
  FILE *f = fopen("/proc/slabinfo", "r");
  if (!f) return -1;
  char line[512]; long total = -1;
  while (fgets(line, sizeof line, f)) {
    if (strncmp(line, "mm_struct ", 10)) continue;
    char *p = strstr(line, "slabdata");
    if (p) { long a = -1; sscanf(p + 8, "%ld %ld", &a, &total); }
    break;
  }
  fclose(f); return total;
}
static void pin0(void) { cpu_set_t s; CPU_ZERO(&s); CPU_SET(0, &s); sched_setaffinity(0, sizeof s, &s); }

static pid_t kids[MAXK];
static int mfds[MAXK];
static int n;
static void add_kid(void) {
  pid_t p = fork();
  if (p == 0) { pin0(); for (;;) pause(); }
  kids[n] = p;
  char path[64]; snprintf(path, sizeof path, "/proc/%d/mem", p);
  mfds[n] = (p > 0) ? open(path, O_RDONLY) : -1;
  n++;
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

  int starts[MAXST]; int ns = 0;
  long prev = mm_slabs();
  printf("base slabs=%ld objs=%ld\n", prev, mm_field(2));
  while (n < MAXK - 40 && ns < MAXST) {
    add_kid();
    long s = mm_slabs();
    if (s > prev) { starts[ns++] = n - 1; prev = s; }
  }
  for (int j = 0; j < 36; j++) add_kid();   /* ensure last slab is filled */
  printf("allocated n=%d slabs=%ld starts(%d):", n, mm_slabs(), ns);
  for (int i = 0; i < ns; i++) printf(" %d", starts[i]);
  printf("\n");

  /* Phase 1: no churn, test slab = starts[0] */
  for (int k = starts[0]; k < starts[0] + 35; k++) free_kid(k);
  long s1 = mm_slabs();
  free_kid(starts[0] + 35);
  long s2 = mm_slabs();
  printf("P1 no-churn: after free35 slabs=%ld, after free last slabs=%ld (drop=%ld)\n",
         s1, s2, s1 - s2);

  /* Phase 2: churn, test slab = starts[1], churn = first object of starts[2..ns-1] */
  for (int k = starts[1]; k < starts[1] + 35; k++) free_kid(k);
  long c0 = mm_slabs();
  int churn = 0;
  for (int c = 2; c < ns && c < 2 + 19; c++) { free_kid(starts[c]); churn++; }
  long c1 = mm_slabs();
  free_kid(starts[1] + 35);
  long c2 = mm_slabs();
  printf("P2 churn(%d): after free35 slabs=%ld, after churn slabs=%ld, after last slabs=%ld (drop=%ld)\n",
         churn, c0, c1, c2, c1 - c2);

  for (int i = 0; i < n; i++) free_kid(i);
  printf("cleanup slabs=%ld\n", mm_slabs());
  return 0;
}
