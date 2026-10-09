#!/bin/bash
S=/root/ghostlock/src/g9700
echo "###### struct miscdevice (source) ######"
awk '/^struct miscdevice {/,/^};/' $S/include/linux/miscdevice.h
echo
echo "###### kallsyms: ashmem_misc ######"
grep -nE ' ashmem_misc$' /root/ghostlock/kernel/kallsyms_fixed.txt
echo
echo "###### main.c: ASHMEM_MISC_FOPS_OFF override + comment ######"
grep -nE 'ASHMEM_MISC_FOPS_OFF|miscdevice\+0x10|fops at' /root/ghostlock/ghostlock-oneplus/src/core/main.c /root/ghostlock/ghostlock-oneplus/src/core/target.h
