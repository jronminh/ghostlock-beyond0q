#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
cat > kernel/probe_pipe.c <<'EOF'
#include <linux/sched.h>
#include <linux/pipe_fs_i.h>
#include <linux/mm_types.h>
#include <linux/mm.h>
const unsigned long pipe_probe[] = {
	offsetof(struct pipe_inode_info, head),
	offsetof(struct pipe_inode_info, tail),
	offsetof(struct pipe_inode_info, max_usage),
	offsetof(struct pipe_inode_info, ring_size),
	offsetof(struct pipe_inode_info, nr_accounted),
	offsetof(struct pipe_inode_info, readers),
	offsetof(struct pipe_inode_info, writers),
	offsetof(struct pipe_inode_info, files),
	offsetof(struct pipe_inode_info, tmp_page),
	offsetof(struct pipe_inode_info, bufs),
	offsetof(struct pipe_inode_info, user),
	sizeof(struct pipe_inode_info),
	offsetof(struct pipe_buffer, page),
	offsetof(struct pipe_buffer, offset),
	offsetof(struct pipe_buffer, len),
	offsetof(struct pipe_buffer, flags),
	offsetof(struct pipe_buffer, ops),
	sizeof(struct pipe_buffer),
	sizeof(struct page),
};
EOF
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out CC=aarch64-linux-gnu-gcc kernel/probe_pipe.o 2>&1 | grep -iE 'error' | head
aarch64-linux-gnu-objcopy -O binary --only-section=.rodata out/kernel/probe_pipe.o /tmp/pipe.bin 2>/dev/null
python3 -c "
import struct
d=open('/tmp/pipe.bin','rb').read()
v=[struct.unpack_from('<Q',d,i)[0] for i in range(0,(len(d)//8)*8,8)]
names=['pii.head','pii.tail','pii.max_usage','pii.ring_size','pii.nr_accounted','pii.readers','pii.writers','pii.files','pii.tmp_page','pii.bufs','pii.user','sizeof(pii)','pbuf.page','pbuf.offset','pbuf.len','pbuf.flags','pbuf.ops','sizeof(pbuf)','sizeof(page)']
for n,x in zip(names,v): print('%-18s 0x%X (%d)'%(n,x,x))
" 2>&1