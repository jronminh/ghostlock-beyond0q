#!/bin/bash
S=/root/ghostlock/src/g9700
echo "==check_version=="
awk '/^static int check_version\(/,/^}/' "$S/kernel/module.c"
echo "==resolve_symbol (modversions bits)=="
awk '/^static const struct kernel_symbol \*resolve_symbol\(/,/^}/' "$S/kernel/module.c" | sed -n '1,80p'
echo "==where modversions var set=="
grep -n "modversions" "$S/kernel/module.c" | head
