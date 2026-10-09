#!/bin/bash
K=/root/ghostlock/src/g9700
echo "=== 4.14 futex_hashsize formula ==="
grep -n 'futex_hashsize\s*=\|FUTEX_HASHBITS\|roundup_pow_of_two\|num_possible_cpus\|nr_cpu_ids\|futex_queues' $K/kernel/futex.c | head -20
echo
echo "--- futex_init ---"
sed -n '/static int __init futex_init/,/^}/p' $K/kernel/futex.c | head -50
echo
echo "=== 4.14 get_futex_key (private case) ==="
sed -n '/^static int get_futex_key/,/^}/p' $K/kernel/futex.c | sed -n '1,80p' | grep -nE 'private|address|offset|both|PAGE|shift|key->' | head -30
echo
echo "=== exploit: futex_init + how it fills/tests buckets ==="
grep -n 'futex_hashsize\|_SC_NPROCESSORS\|FUTEX_WAIT\|FUTEX_PRIVATE\|hb_waiters\|hash bucket\|increase the hash' /root/ghostlock/ghostlock-oneplus/src/core/kernelsnitch/kernelsnitch.h | head -30
