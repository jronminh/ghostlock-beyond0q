#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus
F=$R/src/core/main.c
echo "main.c lines: $(wc -l < $F)"
echo "=== occurrences ==="
grep -n route_only_mode $R/src/core/*.c $R/src/core/*.h
echo "--- select_offsets ---"
grep -n select_offsets $R/src/core/*.c
echo "--- main( ---"
grep -n "int main" $R/src/core/*.c
echo "=== tail of main.c ==="
tail -80 $F
