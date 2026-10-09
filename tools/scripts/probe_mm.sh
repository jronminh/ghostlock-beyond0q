#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
cat > kernel/probe_mm.c <<'EOF'
#include <linux/sched.h>
#include <linux/mm_types.h>
#include <linux/cred.h>
const unsigned long mm_probe[] = {
	sizeof(struct mm_struct),
	offsetof(struct mm_struct, owner),
	offsetof(struct mm_struct, arg_start),
	sizeof(struct cred),
	sizeof(struct files_struct),
};
EOF
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_mm.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_mm.o /tmp/mm.bin 2>/dev/null
python3 -c "
import struct
d=open('/tmp/mm.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
for n,x in zip(['sizeof(mm_struct)','mm.owner','mm.arg_start','sizeof(cred)','sizeof(files_struct)'],v): print('%-22s 0x%X (%d)'%(n,x,x))
"
echo
echo "=== where is MM_STRUCT_SZ used in kernelsnitch? ==="
cd ~/ghostlock/ghostlock-oneplus
grep -n 'mm_struct_sz\|MM_STRUCT_SZ\|objs_per_slab\|mm_per_slab' src/core/kernelsnitch/kernelsnitch.h src/core/util.c | head
