#!/bin/bash
SRC=/root/ghostlock/ghostlock-oneplus/src/core
K=/root/ghostlock/src/g9700/kernel
echo "===== PSELECT_ROUTE_NFDS / defined ====="
grep -rn "PSELECT_ROUTE_NFDS\|PSELECT_TIMEOUT\|PSELECT_CONSUMER\|PSELECT_ENTER_DELAY\|SELECT_STACK_ALLOC" $SRC/ 2>/dev/null | head -30
echo
echo "===== fs/select.c: struct fd_set_bits + core_sys_select + compat ====="
grep -n "fd_set_bits\|core_sys_select\|compat_core_sys_select\|SELECT_STACK_ALLOC\|FDS_BYTES\|fds.in\|fds.res_in\|stack_fds\|FDS_LONGS\|bitmap" $K/fs/select.c | head -70
echo
echo "===== compat_get_bitmap / compat_put_bitmap (lib/compat or fs) ====="
grep -rn "compat_get_bitmap\|compat_put_bitmap" $K/include/linux/*.h $K/fs/select.c 2>/dev/null | head
