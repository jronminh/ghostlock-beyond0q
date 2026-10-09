#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
K=/root/ghostlock/kernel
echo "###### 4.14 struct rt_mutex_waiter (source) ######"
sed -n '/^struct rt_mutex_waiter {/,/^};/p' /root/ghostlock/src/g9700/kernel/include/linux/rtmutex.h 2>/dev/null \
 || find /root/ghostlock/src/g9700 -name rtmutex.h | head
echo
echo "###### disasm: 'add x?, x25, #imm' (pi_tree/tree node offsets on the waiter) ######"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
  --start-address=0xffffff80080b2eec --stop-address=0xffffff80080b3720 \
  | grep -nE 'add\s+x[0-9]+, x25, #|add\s+x[0-9]+, x2[0-9], #|add\s+x[0-9]+, x19, #0x930|add\s+x[0-9]+, x19, #0x948' | head -40
echo
echo "###### rt_mutex_enqueue_pi / dequeue_pi / top_waiter symbols ######"
grep -nE 'rt_mutex_(enqueue|dequeue|top_waiter|enqueue_pi|dequeue_pi|adjust_prio)$' $K/kallsyms_fixed.txt
