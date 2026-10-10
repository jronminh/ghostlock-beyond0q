#!/bin/bash
S=/root/ghostlock/src/g9700/security/defex_lsm
echo "== Makefile =="
cat "$S/Makefile" 2>&1
echo "== Kconfig =="
cat "$S/Kconfig" 2>&1
echo "== defex_sysfs.c (store/attrs) =="
grep -n "sysfs\|attribute\|store\|show\|status\|kobj\|DEFEX_PERMISSIVE\|global_privesc\|global_safeplace" "$S/defex_sysfs.c" 2>&1 | head -40
echo "== global_*obj defs =="
grep -rn "global_privesc_obj\|global_safeplace_obj\|privesc_status\|safeplace_status\|->status" "$S" 2>/dev/null | head -30
echo "== CONFIG_DEFEX_PERMISSIVE? =="
grep -iE 'DEFEX_PERMISSIVE|PERMISSIVE_PED|PERMISSIVE_SP|DEFEX_PED|DEFEX_SAFEPLACE' /root/ghostlock/src/g9700/out/.config
