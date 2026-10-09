#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "### pselect_custom_write_enabled ###"
grep -rn "pselect_custom_write_enabled" $R/*.c $R/*.h
echo
sed -n '/pselect_custom_write_enabled(void)/,/^}/p' $R/util.c $R/fops.c 2>/dev/null
echo
echo "### run_exploit: các bước setup đầu (ảnh hưởng con) ###"
sed -n '/^int run_exploit/,/UMH path/p' $R/main.c | head -80
echo
echo "### set_limit / pin_to_core / disable_rseq (định nghĩa) ###"
sed -n '/void set_limit/,/^}/p' $R/util.c
sed -n '/int pin_to_core/,/^}/p' $R/util.c
