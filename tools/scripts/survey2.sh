#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src
echo "###### target.h: payload-page layout ######"
grep -nE 'LOCK_OFF|W0_OFF|FAKE_TASK_OFF|FOPS_TABLE_OFF|SKB_DATA_DELTA|SCRATCH_OFF|LEFT_OFF|FOPS_OFF|CRED_COPY_OFF|FAKE_WAITER_|FAKE_TASK_|FAKE_WAITER_PRIO|FAKE_TASK_PRIO|WAITER_|SKB_|ORDER3' $R/core/target.h | head -70
echo
echo "###### runtime_struct_offsets.h (RSO) ######"
cat $R/core/runtime_struct_offsets.h
echo
echo "###### beyond0q/offsets.h: task_struct pi_* + waiter ######"
grep -nE 'task_pi_|task_prio|task_cred|task_comm|waiter_compact|task_pid' $R/devices/beyond0q/offsets.h
