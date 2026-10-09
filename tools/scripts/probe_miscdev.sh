#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
cat > kernel/probe_miscdev.c <<'EOF'
#include <linux/sched.h>
#include <linux/miscdevice.h>
const unsigned long md_probe[] = {
	offsetof(struct miscdevice, minor),
	offsetof(struct miscdevice, name),
	offsetof(struct miscdevice, fops),
	offsetof(struct miscdevice, list),
	sizeof(struct miscdevice),
};
EOF
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_miscdev.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_miscdev.o /tmp/md.bin 2>/dev/null
python3 - <<'PY'
import struct
d=open('/tmp/md.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
names=['miscdevice.minor','miscdevice.name','miscdevice.fops','miscdevice.list','sizeof(miscdevice)']
for n,x in zip(names,v): print('%-20s 0x%X'%(n,x))
PY
echo "=== how ASHMEM_MISC_FOPS used ==="
grep -rn 'ASHMEM_MISC_FOPS' /root/ghostlock/ghostlock-oneplus/src/core/*.c | head