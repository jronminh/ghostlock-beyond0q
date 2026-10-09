/* slubtest: does freeing a full mm_struct slab (35 then last object) return the
 * page to the buddy on THIS 4.14 kernel, with and without the per-CPU partial
 * drain churn?  Non-destructive: only forks/opens /proc/pid/mem/reads slabinfo. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <sched.h>
#include <string.h>

#define MAXK 4096

static long mm_slabs(void) {
  FILE *f = fopen("/proc/slabinfo", "r");
  if (!f) return -1;
  char line[512];
  long total = -1;
  while (fgets(line, sizeof line, f)) {
    if (strncmp(line, "mm_struct ", 10)) continue;
    char *p = strstr(line, "slabdata");
    if (p) { long a = -1; sscanf(p + 8, "%ld %ld", &a, &total); }
    break;
  }
  fclose(f);
  return total;
}
static void pin0(void) {
  cpu_set_t s; CPU_ZERO(&s); CPU_SET(0, &s);
  sched_setaffinity(0, sizeof s, &s);
}
static pid_t kids[MAXK];
static int mfds[MAXK];
static pid_t spawn(void) {
  pid_t p = fork();
  if (p == 0) { pin0(); for (;;) pause(); }
  return p;
}
static void free_kid(int i) {
  if (mfds[i] > 0) { close(mfds[i]); mfds[i] = -1; }
  if (kids[i] > 0) { kill(kids[i], SIGKILL); waitpid(kids[i], NULL, 0); kids[i] = 0; }
}
static void alloc_kids(int from, int to) {
  for (int i = from; i < to && i < MAXK; i++) {
    kids[i] = spawn();
    char p[64];
    snprintf(p, sizeof p, "/proc/%d/mem", kids[i]);
    mfds[i] = open(p, O_RDONLY);
  }
  sched_yield();
}

int main(int argc, char **argv) {
  setvbuf(stdout, NULL, _IONBF, 0);
  pin0();
  const int OBJ = 36;
  int mode = (argc > 1) ? atoi(argv[1]) : 0;

  long base = mm_slabs();
  printf("start mm_slabs=%ld\n", base);

  /* 3 fresh slabs. NB: allocations come from CPU0's per-cpu slab. */
  alloc_kids(0, OBJ * 3);
  printf("after alloc 3 slabs mm_slabs=%ld (delta=%ld)\n", mm_slabs(), mm_slabs() - base);

  /* free 35 of slab0 (mimic pre_ctx), leaving inuse=1 */
  for (int i = 0; i < 35; i++) free_kid(i);
  printf("after free 35/36 mm_slabs=%ld\n", mm_slabs());

  if (mode == 0) {
    printf("mode0: no churn\n");
    free_kid(35);
    printf("after free last (no churn) mm_slabs=%ld\n", mm_slabs());
  } else {
    int extra_from = OBJ * 3;
    int extra = OBJ * 24;
    alloc_kids(extra_from, extra_from + extra);
    printf("after extra %d slabs mm_slabs=%ld\n", 24, mm_slabs());
    printf("mode1: churn = free first object of 20 more full slabs\n");
    for (int s = 3; s < 23; s++) free_kid(s * OBJ);
    printf("after churn20 mm_slabs=%ld\n", mm_slabs());
    free_kid(35);
    printf("after free last (with churn) mm_slabs=%ld\n", mm_slabs());
  }
  printf("done\n");
  return 0;
}
