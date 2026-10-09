#!/bin/bash
cd "$HOME/ghostlock/kernel"
echo "=== all configfs_* in kallsyms.txt ==="
grep -E ' [tT] configfs_' kallsyms.txt
echo
echo "=== all configfs_* in kallsyms_fixed.txt ==="
grep -E ' [tT] configfs_' kallsyms_fixed.txt
