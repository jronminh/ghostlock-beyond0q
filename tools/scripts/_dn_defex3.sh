#!/bin/bash
G="$HOME/ghostlock/src/g9700/security/defex_lsm"
echo "=== defex_ht.c ==="
sed -n '1,80p' "$G/defex_ht.c"
echo "=== grep hook-ish in dir ==="
grep -rn -e "security_hook_list" -e "LSM_HOOK" -e "inode_permission" -e "bprm_check" "$G" 2>/dev/null | head -30
