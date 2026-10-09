#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### end of prepare_kernel_page (sau prepare_skb_payload) ######"
awk '/^uintptr_t prepare_kernel_page/,/^}/' $R/util.c | sed -n '85,200p'
echo
echo "###### kernelsnitch_cleanup (định nghĩa + nơi gọi) ######"
grep -rn "kernelsnitch_cleanup" $R/
sed -n '/void kernelsnitch_cleanup/,/^}/p' $R/kernelsnitch/kernelsnitch.h
echo
echo "###### clone_child / kill_child / clone_leak_child / open_memfd ######"
sed -n '/clone_child(/,/^}/p' $R/util.c | head -40
sed -n '/void kill_child/,/^}/p' $R/util.c
sed -n '/int open_memfd/,/^}/p' $R/util.c
echo
echo "###### cleanup_page_prepare_state + close_reclaim_sockets ######"
sed -n '/cleanup_page_prepare_state/,/^}/p' $R/util.c | head -40
sed -n '/close_reclaim_sockets/,/^}/p' $R/util.c | head -20
