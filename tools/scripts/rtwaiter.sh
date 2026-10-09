#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
echo "=== rt_mutex_waiter def ==="
grep -rn 'struct rt_mutex_waiter {' kernel/locking/
f=$(grep -rl 'struct rt_mutex_waiter {' kernel/locking/ | head -1)
echo "file: $f"
sed -n '/struct rt_mutex_waiter {/,/};/p' "$f"
echo
echo "=== rt_mutex struct ==="
sed -n '/^struct rt_mutex {/,/};/p' "$f"
echo
echo "=== config flags ==="
grep -E 'CHECKPOINT_RESTORE|SCHED_CORE|RT_MUTEX|DEBUG_RT_MUTEXES|PROVE_LOCKING' out/.config
