#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "=== do_pselect_fake_lock_route decls/uses ==="
grep -rn "do_pselect_fake_lock_route" $R/
echo "=== socket/setsockopt includes ==="
grep -rn "sys/socket.h\|SOL_SOCKET\|setsockopt" $R/*.c $R/*.h | head
echo "=== common.h around route decls ==="
grep -n "waiter_thread\|owner_thread\|consumer_thread\|route_delay_usec\|fops_elapsed\|pselect_walk_done\|pselect_custom_write_enabled\|put64\|INIT_TASK\|text_addr" $R/common.h | head -40
echo "=== put64 helper ==="
grep -rn "put64\b" $R/fops.c $R/util.c $R/common.h | head
