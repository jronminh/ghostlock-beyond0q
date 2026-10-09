#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
APC=0xffffff80080b2eec
echo "###### get_task_struct inline in adjust_prio_chain: atomic_inc on [task+usage] ######"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
  --start-address=$APC --stop-address=$((APC+0x830)) \
  | grep -nE 'prfm|ldxr|stxr|add\s+w[0-9]+, w[0-9]+, #0x1' | head -30
echo
echo "###### do_one_write (main.c) ######"
sed -n '/static int do_one_write/,/^}/p' /root/ghostlock/ghostlock-oneplus/src/core/main.c
echo
echo "###### UMH flow / mode selection (grep) ######"
grep -n "UMH path\|do_one_write(\|mode=\|MODE_\|fops redirect\|run_exploit" /root/ghostlock/ghostlock-oneplus/src/core/main.c | head -40
