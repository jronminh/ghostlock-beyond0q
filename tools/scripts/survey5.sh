#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src
echo "###### rt_mutex_waiter struct definition ######"
grep -rn "struct rt_mutex_waiter {" $R/../../src/g9700/include/ 2>/dev/null
grep -rln "rt_mutex_waiter {" /root/ghostlock/src/g9700/ 2>/dev/null | head
echo
echo "###### usages of WAITER_* (không phải FAKE_) ######"
grep -rnE '\bWAITER_[A-Z_]+' $R/core/*.c $R/core/*.h | grep -v FAKE_WAITER | head -30
echo
echo "###### usages of FAKE_WAITER_* ######"
grep -rnE 'FAKE_WAITER_[A-Z_]+' $R/core/*.c $R/core/*.h | head -30
echo
echo "###### FAKE_TASK_USAGE_OFF dùng ở đâu / giá trị ######"
grep -rn 'FAKE_TASK_USAGE_OFF' $R/core/*.c $R/core/*.h
