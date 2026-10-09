#!/usr/bin/env python3
# COMPAT32 (AArch32) route: use the compat `select` syscall (ARM _newselect = 142)
# whose stack_fds sits at SP0-0x1e0 => waiter word 6 (shift 6), i.e. task/lock
# land in ex word2/3 = the direct user-writable region.  No res_* needed, so
# select can block and the paint survives.
#
# User fd_set is 32-bit words; the kernel's compat_get_bitmap() assembles
#   internal_word[k] = ((unsigned)user32[2k+1]<<32) | user32[2k].
p = 'src/core/fops.c'
s = open(p).read()

# 1) 64-bit value <-> two 32-bit compat words
old = '''void fdset_put_word(fd_set *set, int word, uint64_t value) {
  unsigned long *bits = (unsigned long *)set;
  bits[word] = (unsigned long)value;
}

uint64_t fdset_get_word(const fd_set *set, int word) {
  const unsigned long *bits = (const unsigned long *)set;
  return bits[word];
}'''
new = '''void fdset_put_word(fd_set *set, int word, uint64_t value) {
#ifdef COMPAT32
  /* compat_get_bitmap(): internal word k == user32[2k] | user32[2k+1]<<32 */
  uint32_t *bits = (uint32_t *)set;
  bits[2 * word] = (uint32_t)value;
  bits[2 * word + 1] = (uint32_t)(value >> 32);
#else
  unsigned long *bits = (unsigned long *)set;
  bits[word] = (unsigned long)value;
#endif
}

uint64_t fdset_get_word(const fd_set *set, int word) {
#ifdef COMPAT32
  const uint32_t *bits = (const uint32_t *)set;
  return ((uint64_t)bits[2 * word + 1] << 32) | bits[2 * word];
#else
  const unsigned long *bits = (const unsigned long *)set;
  return bits[word];
#endif
}'''
assert s.count(old) == 1, 'fdset fns'
s = s.replace(old, new, 1)

# 2) compat-aware fd bit test for open_selected_fds
old = '''void open_selected_fds(
    fd_set *in, fd_set *out, fd_set *ex, int read_fd, int write_fd) {'''
new = '''#ifdef COMPAT32
static int compat_fd_isset(const fd_set *set, int fd) {
  const uint32_t *w = (const uint32_t *)set;
  int k = fd / 64, j = fd % 64;
  return (w[2 * k + (j >> 5)] >> (j & 31)) & 1u;
}
#define FD_ISSET(fd, set) compat_fd_isset((set), (fd))
#endif

void open_selected_fds(
    fd_set *in, fd_set *out, fd_set *ex, int read_fd, int write_fd) {'''
assert s.count(old) == 1, 'open_selected_fds'
s = s.replace(old, new, 1)

# 3) block_fd: COMPAT32 must use an EMPTY pipe read end so do_select BLOCKS
old = '''    int block_fd = (int)syscall(SYS_timerfd_create, CLOCK_MONOTONIC, 0);
    if (block_fd < 0) {
      pr_warning("pselect timerfd_create failed errno=%d; using pipe read end\\n",
                 errno);
      block_fd = pipefd[0];
    }
    if (block_fd >= 0 && block_fd != pipefd[0]) {'''
new = '''#ifdef COMPAT32
    int block_fd = pipefd[0]; /* empty read end: do_select will block */
#else
    int block_fd = (int)syscall(SYS_timerfd_create, CLOCK_MONOTONIC, 0);
    if (block_fd < 0) {
      pr_warning("pselect timerfd_create failed errno=%d; using pipe read end\\n",
                 errno);
      block_fd = pipefd[0];
    }
#endif
    if (block_fd >= 0 && block_fd != pipefd[0]) {'''
assert s.count(old) == 1, 'block_fd'
s = s.replace(old, new, 1)

# 4) select: COMPAT32 uses the compat select syscall (ARM _newselect = 142)
old = '''    int ret = select(PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);'''
new = '''#ifdef COMPAT32
    int ret = syscall(142 /* ARM _newselect -> compat_sys_select */,
                      PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);
#else
    int ret = select(PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);
#endif'''
assert s.count(old) == 1, 'select'
s = s.replace(old, new, 1)
open(p, 'w').write(s)
print('patched fops.c for COMPAT32')

# 5) consumer: COMPAT32 has no park-handshake; fire during the blocking select
p = 'src/core/main.c'
s = open(p).read()
old = '''    /* Park until the waiter thread has finished select() and res_in holds the
     * fake rt_mutex_waiter (task/lock). */
    for (int spin = 0;'''
new = '''#ifdef COMPAT32
    /* shift=6: task/lock are in the direct user bitmaps, painted at select()
     * entry; fire while do_select is blocked (no park handshake). */
#else
    /* Park until the waiter thread has finished select() and res_in holds the
     * fake rt_mutex_waiter (task/lock). */
    for (int spin = 0;'''
assert s.count(old) == 1, 'consumer park'
s = s.replace(old, new, 1)
# close the #else with #endif right after that loop
old = '''         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }'''
new = '''         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }
#endif'''
assert s.count(old) == 1, 'park close'
s = s.replace(old, new, 1)
open(p, 'w').write(s)
print('patched main.c consumer for COMPAT32')
