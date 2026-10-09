#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus"
echo "=== BAN_GIAO mentions of UMH / unbound / wake ==="
grep -n -i -e "system_unbound" -e "umh" -e "usermodehelper" -e "PTY" -e "wake" "$G/BAN_GIAO.md" | head -40
echo
echo "=== git log touching umh_root.c ==="
git -C "$G" log --oneline -- src/core/umh_root.c | head
echo
echo "=== 4.14 kernel/umh.c exec_work ==="
awk '/call_usermodehelper_exec_work/,/^}/' "$HOME/ghostlock/src/g9700/kernel/umh.c"
