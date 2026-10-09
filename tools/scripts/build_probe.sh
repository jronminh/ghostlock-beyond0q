#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
mkdir -p out
echo "=== defconfig ==="
make O=out beyond0qlte_can_single_defconfig 2>&1 | tail -15
echo
echo "=== prepare ==="
make O=out prepare 2>&1 | tail -25
echo
echo "=== probe.c ==="
cat > kernel/probe_offsets.c <<'EOF'
#include <linux/sched.h>
#include <linux/sched/mm.h>
#include <linux/sched/task.h>
#include <linux/mm.h>
#include <linux/cred.h>
#include <linux/seccomp.h>

const unsigned long probe_offsets[] = {
	offsetof(struct task_struct, pid),
	offsetof(struct task_struct, tgid),
	offsetof(struct task_struct, comm),
	offsetof(struct task_struct, cred),
	offsetof(struct task_struct, real_cred),
	offsetof(struct task_struct, tasks),
	offsetof(struct task_struct, prio),
	offsetof(struct task_struct, normal_prio),
	offsetof(struct task_struct, sched_task_group),
	offsetof(struct task_struct, pi_lock),
	offsetof(struct task_struct, pi_waiters),
	offsetof(struct task_struct, pi_top_task),
	offsetof(struct task_struct, pi_blocked_on),
	offsetof(struct task_struct, mm),
	offsetof(struct task_struct, real_parent),
	offsetof(struct task_struct, atomic_flags),
	offsetof(struct task_struct, seccomp),
	offsetof(struct task_struct, thread),
	sizeof(struct task_struct),
};
EOF
echo "=== build single object ==="
make O=out kernel/probe_offsets.o 2>&1 | tail -25
echo
echo "=== dump offsets from object ==="
if [ -f out/kernel/probe_offsets.o ]; then
  aarch64-linux-gnu-objdump -s -j .rodata out/kernel/probe_offsets.o 2>/dev/null | head -20
  echo "--- or .data ---"
  aarch64-linux-gnu-objdump -s -j .data out/kernel/probe_offsets.o 2>/dev/null | head -20
fi
