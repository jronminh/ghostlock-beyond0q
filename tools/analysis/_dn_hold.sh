#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src/core"
echo "=== SSOPT_HOLD / hold pipe ==="
grep -rn -e "SSOPT_HOLD" -e "ssopt_hold" -e "SSOPT_QUIET_EXIT" "$G" | head -30
echo
echo "=== hold pipe usage body ==="
awk '/if \(env_flag\("SSOPT_HOLD"/{f=1} f{print NR": "$0} f&&/^  \}/{c++; if(c>2) exit}' "$G/fops.c" | head -60
