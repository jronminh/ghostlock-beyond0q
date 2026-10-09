#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src
K=/root/ghostlock/kernel
echo "###### prepare_fake_fops (util.c) ######"
awk '/prepare_fake_fops|fake_fops\[|FOPS_TABLE/,/^}/' $R/core/util.c | sed -n '1,60p'
echo
echo "###### nơi dùng ASHMEM_MISC_FOPS / off_ashmem_misc_fops ######"
grep -rnE 'ASHMEM_MISC_FOPS\b|off_ashmem_misc_fops' $R/core/*.c $R/core/*.h $R/devices/beyond0q/offsets.h
echo
echo "###### beyond0q: off_* ảnh hưởng redirect ######"
grep -nE 'off_noop_llseek|off_configfs|off_ashmem|off_cap_capable|off_copy_splice' $R/devices/beyond0q/offsets.h
echo
echo "###### resolve các offset đó về symbol thật ######"
python3 - <<'PY'
import re,bisect
syms=[]
for l in open('/root/ghostlock/kernel/kallsyms_fixed.txt'):
    m=re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)',l)
    if m: syms.append((int(m.group(1),16),m.group(3)))
syms.sort(); A=[a for a,_ in syms]
base=0xffffff8008000000
want={'off_noop_llseek':0x0020B474,'off_configfs_read_iter':0x002BE7DC,
      'off_configfs_bin_write_iter':0x002BE96C,'off_cap_capable_active':0x00411DCC,
      'off_ashmem_ioctl':0x01043F9C,'off_ashmem_compat_ioctl':0x010447F4,
      'off_ashmem_mmap':0x0104484C,'off_ashmem_open':0x010449BC,'off_ashmem_release':0x01044A3C,
      'off_ashmem_misc_fops(0x2bb1750)':0x02BB1750,'off_ashmem_misc+0x10':0x02BB1760}
for k,o in want.items():
    a=base+o
    i=bisect.bisect_right(A,a)-1
    print(f'{k:34s} +{o:#010x} -> {syms[i][1]:40s} (delta {a-syms[i][0]:#x})')
PY
