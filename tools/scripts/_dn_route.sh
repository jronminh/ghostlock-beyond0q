#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src/core"
echo "=== try_cfi_stage call sites ==="
grep -rn "try_cfi_stage" "$G"
echo
echo "=== do_setsockopt_fake_lock_route ==="
awk '/void do_setsockopt_fake_lock_route/{f=1} f{print} f&&/^}/{exit}' "$G/main.c"
echo
echo "=== waiter_thread / owner_thread (start) ==="
sed -n '120,182p' "$G/main.c"
