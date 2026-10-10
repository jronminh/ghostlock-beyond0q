#!/bin/bash
S=/root/ghostlock/src/g9700
K=/root/ghostlock/kernel/kallsyms_fixed.txt
echo "== .config: samsung security knobs =="
grep -iE 'DEFEX|RKP|KNOX|SECURITY_SELINUX|DM_VERITY|SEC_|SAMSUNG|TIMA|FIVE|INTEGRITY|HARDENED|MODULE_SIG|SECCOMP|KASAN' "$S/out/.config" | head -70
echo
echo "== kallsyms: rkp / defex / knox / integrity =="
grep -iE 'rkp|defex|knox|integrity|sds_|tima|five_|sec_cred|__security' "$K" | head -70
echo
echo "== source dirs (security-ish) =="
ls "$S/security" 2>/dev/null
find "$S" -maxdepth 3 -type d \( -iname '*rkp*' -o -iname '*defex*' -o -iname '*tima*' -o -iname '*five*' -o -iname '*defex*' \) 2>/dev/null | head
echo
echo "== config: rkp/defex detail =="
grep -rn 'CONFIG_RKP\|CONFIG_DEFEX\|CONFIG_SECURITY_DEFEX\|CONFIG_TIMA\|CONFIG_FIVE\|CONFIG_KNOX' "$S/out/.config"
