#!/bin/bash
S=/root/ghostlock/src/g9700
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### struct rt_mutex (source) ######"
awk '/^struct rt_mutex {/,/^};/' $S/include/linux/rtmutex.h
echo
echo "###### disasm offsets used on the fake lock (x24) in adjust_prio_chain ######"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0xffffff8008000000 /root/ghostlock/kernel/Image \
  --start-address=0xffffff80080b2eec --stop-address=0xffffff80080b3720 \
  | grep -oE '\[x24, #(0x[0-9a-f]+|[0-9]+)\]|\[x24\]' | sort | uniq -c
echo
echo "###### payload-page constants (target.h) ######"
grep -nE 'ORDER3|SKB_|PAGE_|LOCK_OFF|W0_OFF|FOPS_OFF|SCRATCH_OFF|LEFT_OFF|FAKE_TASK_OFF|CRED_COPY_OFF' $R/target.h | head -40
echo
echo "###### ORDER3_SIZE / SKB_SEND_SIZE (util.c/common.h) ######"
grep -rnE 'ORDER3_SIZE|SKB_SEND_SIZE|SKB_FRAG_BIAS|SKB_DATA_DELTA|PAGE_SIZE' $R/common.h $R/target.h $R/util.c | head -20
echo
echo "###### struct file_operations (source, 4.14) ######"
awk '/^struct file_operations {/,/^};/' $S/include/linux/fs.h
