#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src/core"
echo "=== grep a/e and root script ==="
grep -rn -e '".*a/e' -e 'ghostlock_root' -e 'run_bootstrap' -e 'ONLY_FOPS' "$G" | head -40
echo
echo "=== run_exploit / bootstrap region ==="
grep -n -e "run_exploit" -e "run_bootstrap" -e "ONLY_FOPS" -e "install_embedded_su" -e "wallpaper" "$G/main.c"
echo
echo "=== STRUCT_PAGE / kmalloc usage sites ==="
grep -rn -e "STRUCT_PAGE_COMPOUND_HEAD_OFF" -e "STRUCT_SLAB_CACHE_OFF" -e "STRUCT_PAGE_TYPE_OFF" -e "KMALLOC_CGROUP_TYPE" "$G"
