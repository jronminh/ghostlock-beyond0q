#!/bin/bash
G="$HOME/ghostlock/src/g9700/security/selinux"
echo "=== sel_write_enforce ==="
awk '/static ssize_t sel_write_enforce/{f=1} f{print} f&&/^}/{exit}' "$G/selinuxfs.c"
echo
echo "=== security.h enforcing_enabled (Samsung) ==="
sed -n '112,132p' "$G/include/security.h"
echo
echo "=== hooks.c 200..235 ==="
sed -n '200,235p' "$G/hooks.c"
