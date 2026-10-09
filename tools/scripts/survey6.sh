#!/bin/bash
awk '/struct rt_mutex_waiter {/,/^};/' /root/ghostlock/src/g9700/kernel/locking/rtmutex_common.h
echo "---- task_struct head (usage offset) ----"
awk '/^struct task_struct {/,/^}/' /root/ghostlock/src/g9700/include/linux/sched.h 2>/dev/null | head -30
