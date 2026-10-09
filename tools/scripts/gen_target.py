#!/usr/bin/env python3
"""Generate a 4.14 target offsets header from kernel/kallsyms_fixed.txt."""
import sys
BASE = 0xffffff8008000000
sym = {}
for line in open('kernel/kallsyms_fixed.txt'):
    p = line.split()
    if len(p) >= 3:
        sym[p[2]] = int(p[0], 16)

def off(name):
    a = sym.get(name)
    return None if a is None else a - BASE

wanted = [
    ('INIT_TASK_OFF', 'init_task'),
    ('INIT_CRED_OFF', 'init_cred'),
    ('INIT_UTS_NS_OFF', 'init_uts_ns'),
    ('EMPTY_ZERO_PAGE_OFF', 'empty_zero_page'),
    ('ROOT_TASK_GROUP_OFF', 'root_task_group'),
    ('SELINUX_ENFORCING_OFF', 'selinux_state'),
    ('KPTR_RESTRICT_OFF', 'kptr_restrict'),
    ('SECURITY_HOOK_HEADS_OFF', 'security_hook_heads'),
    ('KMALLOC_CACHES_OFF', 'kmalloc_caches'),
    ('ANON_PIPE_BUF_OPS_OFF', 'anon_pipe_buf_ops'),
    ('ASHMEM_FOPS_OFF', 'ashmem_fops'),
    ('ASHMEM_MISC_FOPS_OFF', 'ashmem_misc'),
    ('ASHMEM_IOCTL_OFF', 'ashmem_ioctl'),
    ('ASHMEM_COMPAT_IOCTL_OFF', 'compat_ashmem_ioctl'),
    ('ASHMEM_MMAP_OFF', 'ashmem_mmap'),
    ('ASHMEM_OPEN_OFF', 'ashmem_open'),
    ('ASHMEM_RELEASE_OFF', 'ashmem_release'),
    ('ASHMEM_READ_ITER_OFF', 'ashmem_read_iter'),
    ('ASHMEM_SHOW_FDINFO_OFF', None),
    ('CONFIGFS_READ_ITER_OFF', 'configfs_read_bin_file'),
    ('CONFIGFS_BIN_WRITE_ITER_OFF', 'configfs_write_bin_file'),
    ('COPY_SPLICE_READ_OFF', 'generic_file_splice_read'),
    ('NOOP_LLSEEK_OFF', 'noop_llseek'),
    ('SLIDE_NFULNL_LOGGER_OFF', 'nfulnl_logger'),
    ('SLIDE_RANDOM_BOOT_ID_DATA_OFF', 'sysctl_bootid'),
    ('SLIDE_SYSCTL_BOOTID_OFF', 'sysctl_bootid'),
    ('SYSTEM_UNBOUND_WQ_OFF', 'system_unbound_wq'),
    ('CALL_USERMODEHELPER_EXEC_WORK_OFF', 'call_usermodehelper_exec_work'),
    ('CAP_CAPABLE_ACTIVE_OFF', 'cap_capable'),
]

print("// auto-generated for SM-G970W / beyond0qlte / 4.14.190")
print("// KIMAGE_TEXT_BASE = 0x%x  (VA_BITS=39)" % BASE)
out = []
for macro, name in wanted:
    if name is None:
        out.append("#define %-32s 0ULL  // n/a on 4.14" % macro)
        continue
    o = off(name)
    if o is None:
        out.append("#define %-32s 0ULL  // NOT FOUND (%s)" % (macro, name))
    else:
        out.append("#define %-32s 0x%08XULL  // %s" % (macro, o, name))
lg = off('loggers')
out.append("#define %-32s 0x%08XULL  // loggers+0x10" % ('SLIDE_LOGGERS_0_1_OFF', lg + 0x10) if lg
           else "// loggers NOT FOUND")
print('\n'.join(out))
print()
# extra probes
for n in ('loggers', 'cap_capable', 'cap_capable_active', 'security_hook_heads',
          'system_unbound_wq', 'call_usermodehelper_exec_work', 'init_nsproxy',
          'init_fs', 'selinux_blob_sizes', 'configfs_read_file', 'configfs_write_file'):
    o = off(n)
    print("// probe %-34s %s" % (n, ('0x%08X' % o) if o is not None else 'NOT FOUND'))
