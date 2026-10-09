#!/bin/bash
G="$HOME/ghostlock/src/g9700/security/defex_lsm"
echo "=== files ==="
ls "$G"
echo
echo "=== hook registrations ==="
grep -rn -e "security_add_hooks" -e "defex_hooks" -e "\.inode_permission" -e "\.file_permission" -e "\.bprm_check_security" -e "\.mmap" -e "\.file_open" -e "\.sb_mount" "$G" 2>/dev/null | head -40
echo
echo "=== kill usage ==="
grep -rn -e "defex_kill" -e "SIGKILL" -e "do_exit" -e "force_sig" "$G" 2>/dev/null | head -20
