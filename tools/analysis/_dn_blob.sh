#!/bin/bash
K="$HOME/ghostlock/kernel/kallsyms_fixed.txt"
echo "=== selinux blob / lsm symbols ==="
grep -nE ' (selinux_blob_sizes|selinux_cred|selinux_inode_blob_sizes|lsm_blob_sizes)$' "$K"
echo "--- near selinux_state (0xffffff800adc8cc8) ---"
grep -nE '^ffffff800adc8c[0-9a-f]{2}' "$K" | head -12
echo
echo "=== struct lsm_blob_sizes ==="
awk '/struct lsm_blob_sizes \{/{f=1} f{print} f&&/^\};/{exit}' "$HOME/ghostlock/src/g9700/include/linux/lsm_hooks.h" 2>/dev/null
grep -rn "struct lsm_blob_sizes {" "$HOME/ghostlock/src/g9700/include" 2>/dev/null | head
