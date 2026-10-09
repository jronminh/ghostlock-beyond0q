#!/bin/bash
S=/root/ghostlock/src/g9700
echo "### 4.14 rt_mutex_owner / owner flags ###"
grep -rn "rt_mutex_owner\|RT_MUTEX_HAS_WAITERS\|owner =" $S/kernel/locking/rtmutex.c $S/kernel/locking/rtmutex_common.h $S/include/linux/rtmutex.h 2>/dev/null | head -20
echo
echo "### rt_mutex_common.h (nội bộ) ###"
sed -n '1,120p' $S/kernel/locking/rtmutex_common.h
