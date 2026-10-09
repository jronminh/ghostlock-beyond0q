#!/bin/bash
G="$HOME/ghostlock/src/g9700"
echo "=== probe sources ==="
find "$G" -maxdepth 3 -name 'probe_*.c' -printf '%10s %p\n' 2>/dev/null
echo
echo "=== kernel/ dir listing ==="
ls -la "$G/kernel" 2>/dev/null | grep -iE 'probe|Makefile' | head
echo
echo "=== any built vmlinux-related or offset dumps in g9700 ==="
find "$G" -maxdepth 2 \( -name 'probe*' -o -name '*offset*' \) -printf '%10s %p\n' 2>/dev/null | head -40
echo
echo "=== out/kernel listing ==="
ls -la "$G/out/kernel" 2>/dev/null | head -50
