#!/bin/bash
G="$HOME/ghostlock/src/g9700"
echo "=== RKP / KDP / CFG in config ==="
grep -E 'CONFIG_(UH_RKP|RKP_|KNOX_KAP|SECURITY_SELINUX|SECURITY_DEFEX|KPERFMON|TIMA|DM_VERITY)' "$G/out/.config"
echo
echo "=== 4.14 workqueue struct defs ==="
grep -n "struct pool_workqueue {" -A 40 "$G/kernel/workqueue.c" | head -60
