#!/bin/bash
F="$HOME/ghostlock/ghostlock-oneplus/src/core/root.c"
grep -n "install_android_root" "$F"
echo "----------"
awk '/^int install_android_root/{f=1} f{print NR": "$0} f&&/^}/{exit}' "$F" | head -80
