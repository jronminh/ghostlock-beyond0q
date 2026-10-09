#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
K=/root/ghostlock/kernel
D() { aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
      --start-address=$1 --stop-address=$2 | sed -n '6,200p'; }
echo "=== waiter_compact in source ==="
grep -rn "waiter_compact" /root/ghostlock/ghostlock-oneplus/src/ | head
echo
echo "=== task_blocks_on_rt_mutex (sets waiter->task/lock) ==="
grep -nE 'task_blocks_on_rt_mutex$|rt_mutex_enqueue$|rt_mutex_adjust_prio_chain$|rt_mutex_adjust_pi$' $K/kallsyms_fixed.txt
T=$(grep -nE ' task_blocks_on_rt_mutex$' $K/kallsyms_fixed.txt | head -1 | cut -d: -f2 | cut -c1-16)
echo "task_blocks_on_rt_mutex = 0x$T"
D $((0x$T)) $((0x$T+0x140))
