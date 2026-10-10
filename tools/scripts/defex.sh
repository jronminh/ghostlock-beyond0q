#!/bin/bash
S=/root/ghostlock/src/g9700/security/defex_lsm
echo "== ls defex_lsm =="
ls -la "$S" 2>&1
echo "== defex_config.c =="
cat "$S/defex_config.c" 2>&1 | head -100
echo "== include/defex_config.h =="
cat "$S/include/defex_config.h" 2>&1 | head -80
echo "== grep features var =="
grep -rn "get_features\|feature_flag\|defex_features\|DEFEX_FEATURE" "$S" 2>/dev/null | head -30
