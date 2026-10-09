// auto-generated for SM-G970W / beyond0qlte / 4.14.190
// KIMAGE_TEXT_BASE = 0xffffff8008000000  (VA_BITS=39)
#define INIT_TASK_OFF                    0x029A9780ULL  // init_task
#define INIT_CRED_OFF                    0x0220E0D0ULL  // init_cred
#define INIT_UTS_NS_OFF                  0x029A9558ULL  // init_uts_ns
#define EMPTY_ZERO_PAGE_OFF              0x0220B000ULL  // empty_zero_page
#define ROOT_TASK_GROUP_OFF              0x02CE9E80ULL  // root_task_group
#define SELINUX_ENFORCING_OFF            0x02DC8CC8ULL  // selinux_state
#define KPTR_RESTRICT_OFF                0x029A92A8ULL  // kptr_restrict
#define SECURITY_HOOK_HEADS_OFF          0x021F7CA0ULL  // security_hook_heads
#define KMALLOC_CACHES_OFF               0x021F7798ULL  // kmalloc_caches
#define ANON_PIPE_BUF_OPS_OFF            0x017A1600ULL  // anon_pipe_buf_ops
#define ASHMEM_FOPS_OFF                  0x019CCA30ULL  // ashmem_fops
#define ASHMEM_MISC_FOPS_OFF             0x02BB1750ULL  // ashmem_misc
#define ASHMEM_IOCTL_OFF                 0x01043F9CULL  // ashmem_ioctl
#define ASHMEM_COMPAT_IOCTL_OFF          0x010447F4ULL  // compat_ashmem_ioctl
#define ASHMEM_MMAP_OFF                  0x0104484CULL  // ashmem_mmap
#define ASHMEM_OPEN_OFF                  0x010449BCULL  // ashmem_open
#define ASHMEM_RELEASE_OFF               0x01044A3CULL  // ashmem_release
#define ASHMEM_READ_ITER_OFF             0x01043EDCULL  // ashmem_read_iter
#define ASHMEM_SHOW_FDINFO_OFF           0ULL  // n/a on 4.14
#define CONFIGFS_READ_ITER_OFF           0x002BE7DCULL  // configfs_read_bin_file
#define CONFIGFS_BIN_WRITE_ITER_OFF      0x002BE96CULL  // configfs_write_bin_file
#define COPY_SPLICE_READ_OFF             0x0024F2D4ULL  // generic_file_splice_read
#define NOOP_LLSEEK_OFF                  0x0020B474ULL  // noop_llseek
#define SLIDE_NFULNL_LOGGER_OFF          0x0299F4C0ULL  // nfulnl_logger
#define SLIDE_RANDOM_BOOT_ID_DATA_OFF    0x02E86268ULL  // sysctl_bootid
#define SLIDE_SYSCTL_BOOTID_OFF          0x02E86268ULL  // sysctl_bootid
#define SYSTEM_UNBOUND_WQ_OFF            0x02999F88ULL  // system_unbound_wq
#define CALL_USERMODEHELPER_EXEC_WORK_OFF 0x0004FCDCULL  // call_usermodehelper_exec_work
#define CAP_CAPABLE_ACTIVE_OFF           0x00411DCCULL  // cap_capable
#define SLIDE_LOGGERS_0_1_OFF            0x0299F3F0ULL  // loggers+0x10

// probe loggers                            0x0299F3E0
// probe cap_capable                        0x00411DCC
// probe cap_capable_active                 NOT FOUND
// probe security_hook_heads                0x021F7CA0
// probe system_unbound_wq                  0x02999F88
// probe call_usermodehelper_exec_work      0x0004FCDC
// probe init_nsproxy                       0x029B8CF8
// probe init_fs                            0x029E2968
// probe selinux_blob_sizes                 NOT FOUND
// probe configfs_read_file                 0x002BE46C
// probe configfs_write_file                0x002BE59C
