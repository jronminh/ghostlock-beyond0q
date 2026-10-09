#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src
echo "--- beyond0q ---"
grep -nE 'waiter_pi_tree_off|task_usage_off|off_ashmem_misc_fops' $R/devices/beyond0q/offsets.h
echo "--- runtime_struct_offsets.h ---"
grep -nE 'FAKE_WAITER_PI_TREE_ENTRY_OFF|FAKE_TASK_USAGE_OFF' $R/core/runtime_struct_offsets.h
echo "--- offsets struct ---"
grep -nE 'waiter_pi_tree_off|task_usage_off' $R/devices/offsets.h
echo "--- includes runtime_struct_offsets.h ---"
grep -rln 'runtime_struct_offsets.h' $R/core/*.c
