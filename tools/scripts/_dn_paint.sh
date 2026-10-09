#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src/core"
echo "=== SSOPT_EMPTY / waiter paint ==="
grep -rn -e "SSOPT_EMPTY" -e "ssopt_set_waiter_lo" -e "WAITER_LO14" -e "WRITE4_SCRATCH" -e "RB_EMPTY" -e "parent_color" "$G" | head -40
echo
echo "=== ssopt_set_waiter_lo body ==="
awk '/void ssopt_set_waiter_lo/{f=1} f{print NR": "$0} f&&/^}/{exit}' "$G/util.c"
