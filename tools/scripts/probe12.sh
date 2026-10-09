#!/bin/bash
K=/root/ghostlock/src/g9700/kernel
echo "===== futex_requeue(): rt_waiter + task_blocks_on_rt_mutex ====="
grep -n "rt_mutex_waiter\|rt_mutex_start_proxy_lock\|futex_proxy_trylock_atomic\|task_blocks_on_rt_mutex\|requeue_pi" $K/futex.c | sed -n '1,60p'
echo
echo "===== rt_mutex_start_proxy_lock / __rt_mutex_start_proxy_lock ====="
grep -n "start_proxy_lock\|task_blocks_on_rt_mutex\|pi_blocked_on" $K/locking/rtmutex.c | head -40
