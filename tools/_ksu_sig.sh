#!/bin/bash
S=/root/ghostlock/src/g9700
K=/root/ghostlock/kernel/kallsyms_fixed.txt
echo "==module_sig_check=="
awk '/^static int module_sig_check\(/,/^}/' "$S/kernel/module.c"
echo "==sig_enforce defs=="
grep -nE 'sig_enforce|mod_verify_sig|module_sig_check' "$S/kernel/module.c" | head
echo "==kallsyms: enforce/sig/mod_verify=="
grep -iw enforce "$K" | head
grep -iw mod_verify_sig "$K" | head
grep -iw load_module "$K"
echo "==config sig=="
grep -E 'CONFIG_MODULE_SIG|CONFIG_MODULE_REL_CRCS|CONFIG_HAVE_ARCH_PREL32' "$S/out/.config"
