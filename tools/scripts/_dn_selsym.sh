#!/bin/bash
K="$HOME/ghostlock/kernel/kallsyms_fixed.txt"
echo "=== selinux symbols (offsets from KIMAGE 0xffffff8008000000) ==="
grep -nE ' (selinux_enforcing|selinux_state|selinux_enabled|selinux_ops)$' "$K"
echo "--- any 'enforc' ---"
grep -nE 'enforc' "$K" | head
echo "--- any 'selinux' near 0x2dc8 ---"
grep -nE '^ffffff800a(dc8|dd8)' "$K" | head -20
