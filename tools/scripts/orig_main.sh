#!/bin/bash
cd /root/ghostlock/ghostlock-oneplus
echo "===== ORIGINAL main.c: waiter/owner/consumer/run_main_route_threads ====="
git show HEAD:src/core/main.c | sed -n '/void \*waiter_thread/,/^void reset_main_route_state/p'
echo
echo "===== ORIGINAL main.c: consumer_thread ... (nếu chưa in ở trên) ====="
git show HEAD:src/core/main.c | grep -n "consumer_thread\|sched_setattr\|pselect_select_done\|pselect_walk_done\|usleep\|delay_usec" | head -40
