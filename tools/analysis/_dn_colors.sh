#!/bin/bash
G="$HOME/ghostlock/src/g9700"
grep -rn -e "WORK_NR_COLORS" -e "WORK_STRUCT_COLOR_BITS" -e "WORK_STRUCT_FLAG_BITS" "$G/kernel/workqueue.c" "$G/include/linux/workqueue.h"
