#!/bin/bash
set -e
G="$HOME/ghostlock/src/g9700"
cat > "$G/kernel/probe_umh.c" <<'EOF'
#include <linux/workqueue.h>
#include <linux/umh.h>
#include <linux/completion.h>
#include <linux/mm.h>

const unsigned long umh_probe[] = {
	sizeof(struct work_struct),
	offsetof(struct work_struct, data),
	offsetof(struct work_struct, entry),
	offsetof(struct work_struct, func),
	sizeof(struct completion),
	offsetof(struct completion, done),
	sizeof(struct subprocess_info),
	offsetof(struct subprocess_info, work),
	offsetof(struct subprocess_info, complete),
	offsetof(struct subprocess_info, path),
	offsetof(struct subprocess_info, argv),
	offsetof(struct subprocess_info, envp),
	offsetof(struct subprocess_info, wait),
	offsetof(struct subprocess_info, retval),
	offsetof(struct subprocess_info, init),
	offsetof(struct subprocess_info, cleanup),
	offsetof(struct subprocess_info, data),
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
  -DKBUILD_BASENAME='"probe_umh"' -DKBUILD_MODNAME='"probe_umh"' \
  -S -o /tmp/probe_umh.s ../kernel/probe_umh.c
awk '/umh_probe:/{f=1} f{print} /\.size.*umh_probe/{if(f)exit}' /tmp/probe_umh.s
