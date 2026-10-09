#!/bin/bash
F=/root/ghostlock/src/g9700/kernel/futex.c
echo "=== 4.14 futex_wake ==="
sed -n '/^static int futex_wake(/,/^}/p' "$F" | head -60
echo
echo "=== futex_do_wake / match ==="
grep -n 'match_futex\|static int futex_wake\|futex_wake(' "$F" | head
echo
echo "=== plist / chain of bucket ==="
sed -n '/^static int futex_wake(/,/^}/p' "$F" | grep -nE 'hb->chain|plist_for_each|match_futex|ret\+\+|nr_wake|break'