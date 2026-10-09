#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
cat > kernel/probe_cred.c <<'EOF'
#include <linux/sched.h>
#include <linux/cred.h>
const unsigned long cred_probe[] = {
	offsetof(struct cred, uid),
	offsetof(struct cred, gid),
	offsetof(struct cred, euid),
	offsetof(struct cred, egid),
	offsetof(struct cred, fsuid),
	offsetof(struct cred, fsgid),
	offsetof(struct cred, securebits),
	offsetof(struct cred, cap_inheritable),
	offsetof(struct cred, cap_permitted),
	offsetof(struct cred, cap_effective),
	offsetof(struct cred, cap_bset),
	offsetof(struct cred, cap_ambient),
	offsetof(struct cred, security),
	sizeof(struct cred),
};
EOF
unset ARCH; export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_cred.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_cred.o /tmp/cred.bin 2>/dev/null
python3 -c "
import struct
d=open('/tmp/cred.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
for n,x in zip(['cred.uid','cred.gid','cred.euid','cred.egid','cred.fsuid','cred.fsgid','cred.securebits','cred.cap_inh','cred.cap_perm','cred.cap_eff','cred.cap_bset','cred.cap_amb','cred.security','sizeof(cred)'],v): print('%-18s 0x%X (%d)'%(n,x,x))
"