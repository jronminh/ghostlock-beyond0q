#!/bin/bash
echo "###### include/linux/rtmutex.h : struct rt_mutex_waiter ######"
sed -n '/struct rt_mutex_waiter {/,/^};/p' /root/ghostlock/src/g9700/include/linux/rtmutex.h
echo
echo "###### kernel/locking/rtmutex.h (internal) ######"
sed -n '1,80p' /root/ghostlock/src/g9700/kernel/locking/rtmutex.h
echo
echo "###### target.h FAKE_WAITER_* (đang dùng) ######"
grep -n 'FAKE_WAITER' /root/ghostlock/ghostlock-oneplus/src/core/target.h
