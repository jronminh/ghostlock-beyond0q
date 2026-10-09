#!/bin/bash
G="$HOME/ghostlock/src/g9700/security/defex"
ls "$G" 2>/dev/null
echo "=== hooks registered ==="
grep -rn -e "security_add_hooks" -e "LSM_HOOK_INIT" -e "\.bprm_check_security" -e "\.inode_permission" -e "\.file_permission" -e "\.mmap_file" -e "\.file_open" -e "kill" "$G"/*.c 2>/dev/null | head -40
echo
echo "=== defex_kill / defex_kill_processes ==="
grep -rn -e "kill" "$G"/*.c 2>/dev/null | head -30
