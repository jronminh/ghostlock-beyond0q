#!/bin/bash
cd /root/ghostlock/ghostlock-oneplus
echo "###### ORIGINAL do_one_write (git HEAD) ######"
git show HEAD:src/core/main.c | sed -n '/static int do_one_write/,/^}/p'
echo
echo "###### ORIGINAL: try_cfi_stage có được route gọi trực tiếp? ######"
git show HEAD:src/core/fops.c | grep -n "try_cfi_stage()" | head
echo
echo "###### hiện tại: nơi gọi try_cfi_stage ######"
grep -rn "try_cfi_stage()" src/core/*.c
