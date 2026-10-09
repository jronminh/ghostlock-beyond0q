#!/bin/bash
echo "=== exploit futex_hash (kernelsnitch.h) ==="
grep -n 'futex_hash' /root/ghostlock/ghostlock-oneplus/src/core/kernelsnitch/kernelsnitch.h | head
sed -n '/static.*futex_hash/,/^}/p' /root/ghostlock/ghostlock-oneplus/src/core/kernelsnitch/kernelsnitch.h | head -40
echo
echo "=== 4.14 kernel futex hash ==="
K=/root/ghostlock/src/g9700
grep -n 'hash_futex\|futex_hash\|jhash\|hash_long\|futex_hashsize\|futex_queues\[' $K/kernel/futex.c | head -30
echo
echo "--- 4.14 hash_futex body ---"
sed -n '/static inline struct futex_hash_bucket \*hash_futex/,/^}/p' $K/kernel/futex.c
echo
echo "--- 4.14 key layout ---"
sed -n '/union futex_key {/,/};/p' $K/kernel/futex.c
