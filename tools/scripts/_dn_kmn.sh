#!/bin/bash
G="$HOME/ghostlock/src/g9700"
echo "=== definition of struct kmem_cache_node ==="
grep -rn "struct kmem_cache_node {" "$G/include" "$G/mm" 2>/dev/null
echo "=== files defining it ==="
grep -rln "struct kmem_cache_node {" "$G/mm" 2>/dev/null
echo "=== MEMCG_KMEM / SLAB_FREELIST in config ==="
grep -E 'CONFIG_(MEMCG_KMEM|SLAB_FREELIST_HARDENED|SLAB_FREELIST_RANDOM|SLAB_MERGE|SYSFS|SLUB_STATS|NUMA|KASAN)' "$G/out/.config"
echo "=== struct page (mm_types.h) ==="
grep -n "struct page {" "$G/include/linux/mm_types.h"
