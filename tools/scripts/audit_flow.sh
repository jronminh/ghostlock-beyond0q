#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### set_pselect_write_mode / pselect_custom_write_enabled ######"
sed -n '/void set_pselect_write_mode/,/^}/p' $R/fops.c
sed -n '/int pselect_custom_write_enabled/,/^}/p' $R/fops.c
echo
echo "###### các global route phụ thuộc (khai báo + set ở đâu) ######"
grep -rnE 'pselect_custom_write\b|pselect_child_node|route_only_mode|pselect_custom_target|pselect_custom_value' $R/*.c $R/*.h | grep -vE '^\s*\*' | head -40
echo
echo "###### run_route_only (toàn bộ) ######"
sed -n '/static int run_route_only/,/^}/p' $R/main.c
echo
echo "###### do_one_write: chuỗi trước khi fork/exec ######"
sed -n '/static int do_one_write/,/const char \*route_bin/p' $R/main.c
