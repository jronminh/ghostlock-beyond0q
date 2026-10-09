#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
cat > kernel/probe_mm.c <<'EOF'
#include <linux/sched.h>
#include <linux/mm_types.h>
const unsigned long mm_probe[] = {
	sizeof(struct mm_struct),
	offsetof(struct mm_struct, owner),
	offsetof(struct mm_struct, arg_start),
	offsetof(struct mm_struct, mmap_sem),
};
EOF
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_mm.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_mm.o /tmp/mm.bin 2>/dev/null
python3 -c "
import struct
d=open('/tmp/mm.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
for n,x in zip(['sizeof(mm_struct)','mm.owner','mm.arg_start','mm.mmap_sem'],v): print('%-20s 0x%X (%d)'%(n,x,x))
" 2>&1
