#!/bin/bash
R=/root/ghostlock-beyond0q
S=/root/ghostlock/src/g9700
echo "== repo: write_selinux_policy_fix_script (find) =="
grep -rn "write_selinux_policy_fix_script\|ghostlock_fixpol\|fixpol\|selinux_policy" "$R/src" 2>/dev/null | head
echo "== definition =="
F=$(grep -rl "write_selinux_policy_fix_script" "$R/src" 2>/dev/null | head -1)
echo "file=$F"
awk '/write_selinux_policy_fix_script/,/^}/' "$F" 2>/dev/null | head -120
echo
echo "== .config SELinux knobs =="
grep -iE 'CONFIG_SECURITY_SELINUX|CONFIG_SECURITY_SELINUX_DEVELOP|CONFIG_SECURITY_SELINUX_DISABLE|CONFIG_SECURITY_SELINUX_BOOTPARAM|CONFIG_DEFAULT_SECURITY|CONFIG_LSM' "$S/out/.config"
echo
echo "== device selinux props in configs =="
grep -rn "selinux" "$S/out/.config" | grep -iE "permissive|enforcing|bootparam" | head
