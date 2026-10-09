#!/bin/bash
K=/root/ghostlock/src/g9700
echo "=== exploit futex_hash.h ==="
cat /root/ghostlock/ghostlock-oneplus/src/core/kernelsnitch/futex_hash.h
echo
echo "=== 4.14 kernel hash_futex (396-410) ==="
sed -n '396,410p' $K/kernel/futex.c
echo
echo "=== 4.14 futex_key struct ==="
grep -n 'struct futex_key {' $K/kernel/futex.c
sed -n '/^struct futex_key {/,/};/p' $K/kernel/futex.c
echo "--- union futex_key ---"
sed -n '/^union futex_key {/,/};/p' $K/kernel/futex.c
