#!/bin/bash
F="$HOME/ghostlock/src/g9700/kernel/locking/rtmutex.c"
grep -n "rt_mutex_adjust_prio_chain" "$F"
echo "----------- body -----------"
awk '/^static int rt_mutex_adjust_prio_chain/{f=1} f{print NR": "$0} f&&/^}$/{exit}' "$F"
