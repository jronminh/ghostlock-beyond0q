#!/bin/bash
echo "=== full glB7.log ==="
cat /data/local/tmp/glB7.log 2>/dev/null || true
echo
echo "=== selinux_enforcing symbol ==="
grep -E ' (selinux_enforcing|selinux_state)$' "$HOME/ghostlock/kernel/kallsyms_fixed.txt"
echo
echo "=== enforcing now ==="
cat /sys/fs/selinux/enforce 2>/dev/null
echo
echo "=== /data/local/tmp/a perms ==="
ls -laZ /data/local/tmp/a 2>/dev/null || ls -la /data/local/tmp/a
