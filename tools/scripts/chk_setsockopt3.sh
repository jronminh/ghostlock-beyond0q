#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
K=/root/ghostlock/kernel
D() { aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
      --start-address=$1 --stop-address=$2 | sed -n '6,200p'; }
echo "===== symbols ====="
grep -nE 'sys_setsockopt$|__sys_setsockopt$|SyS_setsockopt$|compat_SyS_setsockopt$|__arm64_sys_setsockopt$|do_signal$|get_signal$|fpsimd_restore|rseq_handle|task_work_run$' $K/kallsyms_fixed.txt
echo
echo "===== SyS_setsockopt 0xffffff8009428f54 ====="
D 0xffffff8009428f54 0xffffff8009429020
echo
echo "===== el0_svc 0xffffff8008003bc0 (đường về EL0) ====="
D 0xffffff8008003bc0 0xffffff8008003c60
