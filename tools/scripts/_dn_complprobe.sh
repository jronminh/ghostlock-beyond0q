#!/bin/bash
set -e
G="$HOME/ghostlock/src/g9700"
cat > "$G/kernel/probe_compl.c" <<'EOF'
#include <linux/completion.h>
#include <linux/wait.h>
#include <linux/mm.h>

const unsigned long compl_probe[] = {
	sizeof(struct completion),
	offsetof(struct completion, done),
	sizeof(struct wait_queue_head),
	offsetof(struct wait_queue_head, lock),
	offsetof(struct wait_queue_head, head),
	offsetof(struct wait_queue_head, head) + offsetof(struct list_head, next),
	offsetof(struct wait_queue_head, head) + offsetof(struct list_head, prev),
	/* struct wait_queue_entry / entry func offsets */
	sizeof(struct wait_queue_entry),
	offsetof(struct wait_queue_entry, entry),
	offsetof(struct wait_queue_entry, func),
	offsetof(struct wait_queue_entry, private),
};
EOF
cd "$G/out"
aarch64-linux-gnu-gcc -nostdinc -isystem /usr/lib/gcc-cross/aarch64-linux-gnu/14/include \
  -I../arch/arm64/include -I./arch/arm64/include/generated -I../include -I./include \
  -I../arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I../include/uapi \
  -I./include/generated/uapi -include ../include/linux/kconfig.h -I../kernel -Ikernel \
  -D__KERNEL__ -mlittle-endian -DKASAN_SHADOW_SCALE_SHIFT=3 -fno-strict-aliasing -fno-common \
  -fshort-wchar -std=gnu89 -fno-PIE -mgeneral-regs-only -DCONFIG_AS_LSE=1 \
  -fno-asynchronous-unwind-tables -mpc-relative-literal-loads -fno-pic -mabi=lp64 \
  -fno-delete-null-pointer-checks -O2 -fno-var-tracking-assignments -fno-jump-tables \
  -fno-strict-overflow -fno-merge-all-constants -fmerge-constants \
  -DKBUILD_BASENAME='"probe_compl"' -DKBUILD_MODNAME='"probe_compl"' \
  -S -o /tmp/probe_compl.s ../kernel/probe_compl.c
awk '/compl_probe:/{f=1} f{print} /\.size.*compl_probe/{if(f)exit}' /tmp/probe_compl.s
