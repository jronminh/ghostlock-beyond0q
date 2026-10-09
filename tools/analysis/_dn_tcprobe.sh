#!/bin/bash
set -e
G="$HOME/ghostlock/src/g9700"
cat > "$G/kernel/probe_taskcred.c" <<'EOF'
#include <linux/sched.h>
#include <linux/sched/task.h>
#include <linux/cred.h>
#include <linux/mm.h>

const unsigned long tc_probe[] = {
	offsetof(struct task_struct, real_cred),
	offsetof(struct task_struct, cred),
	offsetof(struct task_struct, pid),
	offsetof(struct task_struct, tgid),
	offsetof(struct task_struct, comm),
	offsetof(struct task_struct, tasks),
	sizeof(struct task_struct),
	offsetof(struct cred, uid),
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
  -DKBUILD_BASENAME='"probe_taskcred"' -DKBUILD_MODNAME='"probe_taskcred"' \
  -S -o /tmp/probe_taskcred.s ../kernel/probe_taskcred.c
awk '/tc_probe:/{f=1} f{print} /\.size.*tc_probe/{if(f)exit}' /tmp/probe_taskcred.s
