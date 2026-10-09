#!/usr/bin/env python3
# slide.c: 4.14 route uses select() -> pselect6 -> waiter at stack_fds word 12.
#   * generalize slide_pselect_put_global_word for res_in/res_out/res_ex
#   * replace the 6.x NESTED words[] with the 4.14 COMPACT layout
#   * arm the timerfd so the selected fds are ready (res_in gets filled)
# Also set SLIDE_PSELECT_WORD_SHIFT=12 in target.h.
import re

# ---------------- slide.c ----------------
p = 'src/core/slide.c'
s = open(p).read()

old_put = '''int slide_pselect_put_global_word(
    fd_set *in, fd_set *out, fd_set *ex, int words_per_set,
    int global_word, uint64_t value) {
  if (global_word < 0) {
    return 0;
  }

  int set_idx = global_word / words_per_set;
  int word_idx = global_word % words_per_set;
  switch (set_idx) {
    case 0:
      fdset_put_word(in, word_idx, value);
      return 1;
    case 1:
      fdset_put_word(out, word_idx, value);
      return 1;
    case 2:
      fdset_put_word(ex, word_idx, value);
      return 1;
    default:
      return 0;
  }
}'''
new_put = '''int slide_pselect_put_global_word(
    fd_set *in, fd_set *out, fd_set *ex, int words_per_set,
    int global_word, uint64_t value) {
  if (global_word < 0) {
    return 0;
  }

  /* bits = in|out|ex|res_in|res_out|res_ex; do_select writes res_X = X & ready.
   * 4.14: waiter @ word 12, so task/lock fall in res_in and are forced by
   * mirroring into the corresponding `in` words. */
  int set_idx = global_word / words_per_set;
  int word_idx = global_word % words_per_set;
  switch (set_idx) {
    case 0: /* in */
    case 3: /* res_in <- in  */
      fdset_put_word(in, word_idx, value);
      return 1;
    case 1: /* out */
    case 4: /* res_out <- out */
      fdset_put_word(out, word_idx, value);
      return 1;
    case 2: /* ex */
    case 5: /* res_ex <- ex  */
      fdset_put_word(ex, word_idx, value);
      return 1;
    default:
      return 0;
  }
}'''
assert old_put in s, 'slide_pselect_put_global_word not found'
s = s.replace(old_put, new_put, 1)

old_words = s[s.index('  struct slide_waiter_word {'):s.index('  for (size_t i = 0;')]
new_words = '''  struct slide_waiter_word {
    int word;
    uint64_t value;
    const char *name;
  } words[] = {
    /* 4.14 COMPACT rt_mutex_waiter (10 words):
     * tree@0, pi_tree@0x18, task@0x30, lock@0x38, prio@0x40, deadline@0x48 */
    {0, SLIDE_LOGGERS_0_1, "tree_pc"},
    {1, 0, "tree_r"},
    {2, SLIDE_RANDOM_BOOT_ID_DATA, "tree_l"},
    {3, SLIDE_LOGGERS_0_1, "pi_pc"},
    {4, 0, "pi_r"},
    {5, SLIDE_RANDOM_BOOT_ID_DATA, "pi_l"},
    {6, SLIDE_INIT_TASK, "task"},
    {7, fake_lock, "lock"},
    {8, FAKE_WAITER_PRIO, "prio"},
    {9, 0, "deadline"},
  };
'''
s = s.replace(old_words, new_words, 1)

# arm the timerfd in slide_pselect_stack_copy
old_tfd = '''  int block_fd = (int)syscall(SYS_timerfd_create, CLOCK_MONOTONIC, 0);
  if (block_fd < 0) {
    pr_warning("slide timerfd_create failed errno=%d; using pipe read end\\n",
               errno);
    block_fd = pipefd[0];
  }'''
new_tfd = '''  int block_fd = (int)syscall(SYS_timerfd_create, CLOCK_MONOTONIC, 0);
  if (block_fd < 0) {
    pr_warning("slide timerfd_create failed errno=%d; using pipe read end\\n",
               errno);
    block_fd = pipefd[0];
  } else {
    /* expire immediately so every selected fd is poll-ready; do_select then
     * writes res_in = in & ready (this is how task/lock get placed). */
    struct itimerspec its;
    memset(&its, 0, sizeof its);
    its.it_value.tv_nsec = 1000;
    syscall(SYS_timerfd_settime, block_fd, 0, &its, NULL);
  }'''
assert old_tfd in s, 'slide timerfd block not found'
s = s.replace(old_tfd, new_tfd, 1)
open(p, 'w').write(s)
print('patched slide.c')

# ---------------- target.h ----------------
p = 'src/core/target.h'
s = open(p).read()
old = '''/* SLIDE mode pselect shift (pselect vs select stack frame diff 16B = 2 words) */
#define SLIDE_PSELECT_WORD_SHIFT 2'''
new = '''/* SLIDE mode also uses select() -> pselect6 -> waiter at stack_fds word 12 */
#define SLIDE_PSELECT_WORD_SHIFT 12'''
assert old in s, 'SLIDE_PSELECT_WORD_SHIFT block not found'
s = s.replace(old, new, 1)
open(p, 'w').write(s)
print('patched target.h SLIDE_PSELECT_WORD_SHIFT=12')
