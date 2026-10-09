#!/bin/bash
F="$HOME/ghostlock/ghostlock-oneplus/src/core/umh_root.c"
grep -n "handle_umh_mode" "$F"
echo "----"
sed -n '/^void handle_umh_mode/,$p' "$F"
