#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
grep -q 'linux/cred.h' kernel/probe_misc.c || sed -i 's|#include <linux/mm.h>|#include <linux/mm.h>\n#include <linux/cred.h>|' kernel/probe_misc.c
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_misc.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_misc.o /tmp/misc.bin 2>/dev/null
python3 - <<'PY'
import struct
d=open('/tmp/misc.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
names=['seccomp.mode','seccomp.filter','sizeof(seccomp)','sizeof(page)','sizeof(mm_struct)','sizeof(cred)']
for n,x in zip(names,v): print('%-18s 0x%X (%d)'%(n,x,x))
PY
