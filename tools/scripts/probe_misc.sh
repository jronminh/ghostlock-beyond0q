#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
cat > kernel/probe_misc.c <<'EOF'
#include <linux/sched.h>
#include <linux/seccomp.h>
#include <linux/mm_types.h>
#include <linux/mm.h>
const unsigned long misc_probe[] = {
	offsetof(struct seccomp, mode),
	offsetof(struct seccomp, filter),
	sizeof(struct seccomp),
	sizeof(struct page),
	sizeof(struct mm_struct),
	sizeof(struct cred),
};
EOF
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_misc.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_misc.o /tmp/misc.bin 2>/dev/null
python3 -c "
import struct
d=open('/tmp/misc.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
names=['seccomp.mode','seccomp.filter','sizeof(seccomp)','sizeof(page)','sizeof(mm_struct)','sizeof(cred)']
for n,x in zip(names,v): print('%-18s 0x%X (%d)'%(n,x,x))
" 2>&1
echo "=== target.h SECCOMP/STRUCT_PAGE ==="
grep -nE 'SECCOMP_|STRUCT_PAGE' /root/ghostlock/ghostlock-oneplus/src/core/target.h