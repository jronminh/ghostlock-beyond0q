#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
echo "=== MM_STRUCT_SZ / MM_ORDER / KSNITCH_COLLISIONS defs ==="
grep -rn 'define MM_STRUCT_SZ\|define MM_ORDER\|define KSNITCH_COLLISIONS\|MM_STRUCT_SZ\b' src/core/*.h src/core/*.c | head
echo
echo "=== getenv knobs in util.c (940-965) ==="
sed -n '935,965p' src/core/util.c
echo
echo "=== kernelsnitch perf usage ==="
grep -n 'perf_event_open\|PERF_TYPE\|perf_event_paranoid\|SYS_perf' src/core/kernelsnitch/kernelsnitch.h | head
echo
echo "=== probe sizeof(struct mm_struct) 4.14 ==="
cd ~/ghostlock/src/g9700
cat > kernel/probe_mm.c <<'EOF'
#include <linux/sched.h>
#include <linux/mm_types.h>
const unsigned long mm_probe[] = {
	sizeof(struct mm_struct),
	offsetof(struct mm_struct, mmap_sem),
	offsetof(struct mm_struct, arg_start),
	offsetof(struct mm_struct, owner),
	sizeof(struct cred),
};
EOF
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_mm.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_mm.o /tmp/mm.bin 2>/dev/null
python3 -c "
import struct
d=open('/tmp/mm.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
for n,x in zip(['sizeof(mm_struct)','mmap_sem','arg_start','owner','sizeof(cred)'],v): print('%-20s 0x%X'%(n,x))
"
