#!/bin/bash
G="$HOME/ghostlock/src/g9700"
grep -rn "KMALLOC_NORMAL" "$G/include" "$G/mm" 2>/dev/null | head
echo "=== enum in slab_common.c / slab.h ==="
grep -rn "kmalloc_cache_type" "$G/include" "$G/mm" 2>/dev/null | head
