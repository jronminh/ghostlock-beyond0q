#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src/core"
echo "=== select_offsets definition ==="
grep -rn "select_offsets" "$G" | head
echo
echo "=== search in util.c around matches ==="
grep -n "select_offsets" "$G/util.c"
echo
echo "=== target.h include sites ==="
grep -rn "TARGET_CONFIG_H" "$G"
grep -rn "include \"target.h\"\|include <target.h>" "$G"
