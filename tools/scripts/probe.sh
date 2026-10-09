#!/bin/bash
SRC=/root/ghostlock/ghostlock-oneplus/src/core
K=/root/ghostlock/kernel
echo "===== target.h ====="
grep -nE 'PSELECT|WAITER|SHIFT|ROUTE_NFDS|CONSUMER|ROUTE_WAIT|ROUTE_DELAY' $SRC/target.h 2>/dev/null | head -80
echo "===== devices beyond0q offsets (waiter) ====="
grep -rnE 'WAITER|SP0|PAGE_PAYLOAD|fake_w' /root/ghostlock/ghostlock-oneplus/src/ 2>/dev/null | grep -iE 'waiter|sp0|fake_w' | head -40
echo "===== fops pselect helpers ====="
grep -nE 'prepare_pselect_fdsets|open_selected_fds|fdset_get_word|fdset_set_word|fake_w0|fake_task|fake_lock|res_' $SRC/fops.c | head -60
echo "===== kern Image / vmlinux ====="
ls -la $K/ | head
file $K/Image 2>/dev/null
ls -la /root/ghostlock/ghostlock-oneplus/src/ | head -40
