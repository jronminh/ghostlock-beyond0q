#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus"
echo "=== umh_root.c key lines ==="
grep -n -e "WQ_DFL_PWQ_OFF" -e "umh: post worklist" -e "tty_schedule_flip" -e "wm == 1" -e "work\[32\]" "$G/src/core/umh_root.c"
echo
echo "=== git status ==="
git -C "$G" status --short
