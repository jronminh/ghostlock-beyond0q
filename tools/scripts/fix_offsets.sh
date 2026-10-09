#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
python3 - <<'PY'
p='src/core/target.h'
s=open(p).read()
vals = {
 'INIT_TASK_OFF':'0x029A9780','INIT_CRED_OFF':'0x0220E0D0','INIT_UTS_NS_OFF':'0x029A9558',
 'EMPTY_ZERO_PAGE_OFF':'0x0220B000','ROOT_TASK_GROUP_OFF':'0x02CE9E80','SELINUX_ENFORCING_OFF':'0x02DC8CC8',
 'KPTR_RESTRICT_OFF':'0x029A92A8','CAP_CAPABLE_ACTIVE_OFF':'0x00411DCC','SELINUX_BLOB_SIZES_OFF':'0x0',
 'SECURITY_HOOK_HEADS_OFF':'0x021F7CA0','KMALLOC_CACHES_OFF':'0x021F7798','ANON_PIPE_BUF_OPS_OFF':'0x017A1600',
 'SYSTEM_UNBOUND_WQ_OFF':'0x02999F88','CALL_USERMODEHELPER_EXEC_WORK_OFF':'0x0004FCDC',
 'CONFIGFS_READ_ITER_OFF':'0x002BE7DC','CONFIGFS_BIN_WRITE_ITER_OFF':'0x002BE96C',
 'COPY_SPLICE_READ_OFF':'0x0024F2D4','NOOP_LLSEEK_OFF':'0x0020B474',
 'ASHMEM_MISC_FOPS_OFF':'0x02BB1750','ASHMEM_FOPS_OFF':'0x019CCA30','ASHMEM_IOCTL_OFF':'0x01043F9C',
 'ASHMEM_COMPAT_IOCTL_OFF':'0x010447F4','ASHMEM_MMAP_OFF':'0x0104484C','ASHMEM_OPEN_OFF':'0x010449BC',
 'ASHMEM_RELEASE_OFF':'0x01044A3C','ASHMEM_SHOW_FDINFO_OFF':'0x0',
 'SLIDE_NFULNL_LOGGER_OFF':'0x0299F4C0','SLIDE_LOGGERS_0_1_OFF':'0x0299F3F0',
 'SLIDE_RANDOM_BOOT_ID_DATA_OFF':'0x02E86268','SLIDE_SYSCTL_BOOTID_OFF':'0x02E86268',
}
import re
cnt=0
for k,v in vals.items():
    pat = re.compile(r'(#define\s+'+k+r'\s+)0x[0-9a-fA-F]+(ULL)?')
    s2,n = pat.subn(lambda m: m.group(1)+v+('ULL' if m.group(2) else ''), s, count=1)
    if n: s=s2; cnt+=1
    else: print("MISS:",k)
open(p,'w').write(s)
print("replaced",cnt,"of",len(vals))
PY
echo "=== verify a few ==="
grep -nE 'define (ASHMEM_IOCTL_OFF|ASHMEM_OPEN_OFF|INIT_TASK_OFF|SLIDE_LOGGERS_0_1_OFF|CONFIGFS_READ_ITER_OFF|NOOP_LLSEEK_OFF)' src/core/target.h
echo "=== rebuild ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock10 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock10 /mnt/e/Library/Desktop/ghostlock/ghostlock10_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock10_a64
