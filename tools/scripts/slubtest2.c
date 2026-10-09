/* slubtest2: single-shot.  Does freeing the first object of N extra full
 * mm_struct slabs (churn) release an already-frozen empty slab back to the
 * buddy (num_slabs drop)?  Non-destructive. */
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

#define OBJ 36
#define NSLAB 18               /* slab0 = test, slabs 1..17 = churn */

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

static pid_t kids[NSLAB * OBJ];
static int mfds[NSLAB * OBJ];

static void alloc_all(void) {
  for (int i = 0; i < NSLAB * OBJ; i++) {
    pid_t p = fork();
    if (p == 0) { pin0(); for (;;) pause(); }
    kids[i] = p;
    char path[64]; snprintf(path, sizeof path, "/proc/%d/mem", p);
    mfds[i] = (p > 0) ? open(path, O_RDONLY) : -1;
  }
  sched_yield();
}
static void free_kid(int i) {
  if (mfds[i] > 0) { close(mfds[i]); mfds[i] = -1; }
  if (kids[i] > 0) { kill(kids[i], SIGKILL); waitpid(kids[i], NULL, 0); kids[i] = 0; }
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);
  struct rlimit r; getrlimit(RLIMIT_NPROC, &r); r.rlim_cur = r.rlim_max; setrlimit(RLIMIT_NPROC, &r);
  pin0();
  long b = mm_slabs();
  printf("start mm_slabs=%ld\n", b);

  alloc_all();
  long after_alloc = mm_slabs();
  printf("after alloc %d slabs mm_slabs=%ld (delta=%ld)\n", NSLAB, after_alloc, after_alloc - b);

  for (int i = 0; i < 35; i++) free_kid(i);              /* slab0 -> partial (frozen) */
  printf("after free 35/36 of slab0 mm_slabs=%ld\n", mm_slabs());

  int churn = 0;
  for (int s = 1; s < NSLAB; s++) { free_kid(s * OBJ); churn++; }   /* first object of each */
  printf("after churn %d full slabs mm_slabs=%ld\n", churn, mm_slabs());

  free_kid(35);                                            /* last object of slab0 */
  long after_last = mm_slabs();
  printf("after free last of slab0 mm_slabs=%ld (drop_from_alloc=%ld)\n",
         after_last, after_alloc - after_last);

  for (int i = 0; i < NSLAB * OBJ; i++) free_kid(i);
  printf("cleanup mm_slabs=%ld done\n", mm_slabs());
  return 0;
}
