#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### util.c: các field FAKE_TASK_* được set ######"
grep -nE 'FAKE_TASK_[A-Z_]+_OFF|FAKE_TASK_OFF \+|pi_waiters|pi_blocked_on|pi_top_task' $R/util.c | head -40
echo
echo "###### đoạn payload quanh FAKE_TASK (util.c ~630-670) ######"
sed -n '628,670p' $R/util.c
