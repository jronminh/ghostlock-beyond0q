#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus"
echo "=== BAN_GIAO mentions: stall/RCU/lockup/prio_chain/flaky ==="
grep -n -i -e "rt_mutex_adjust_prio_chain" -e "rcu" -e "stall" -e "lockup" -e "hard-lock" -e "flaky" -e "watchdog" -e "50%" "$G/BAN_GIAO.md" | head -60
