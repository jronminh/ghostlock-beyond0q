#!/bin/bash
G="$HOME/ghostlock/src/g9700"
echo "=== search vmlinux / System.map / *.o (size) ==="
find "$G/out" -maxdepth 2 \( -name 'vmlinux*' -o -name 'System.map' -o -name '*.o' \) -printf '%10s %p\n' 2>/dev/null | head -40
echo
echo "=== counts ==="
echo -n "out/*.o total: "; find "$G/out" -name '*.o' 2>/dev/null | wc -l
echo -n "slub.o: "; find "$G/out" -name 'slub.o' 2>/dev/null
echo -n "mm dir: "; ls "$G/out/mm" 2>/dev/null | head
echo
echo "=== generated headers ==="
ls -la "$G/out/include/generated/" 2>/dev/null | head -30
echo
echo "=== selected .config options ==="
grep -E 'CONFIG_(SLUB|SLAB|DEBUG_INFO|DEBUG_INFO_DWARF|MEMCG|NUMA|SLUB_CPU_PARTIAL|SLUB_DEBUG|KMEMLEAK|SLAB_FREELIST|RANDOMIZE_BASE|ARM64_VA_BITS|HARDENED_USERCOPY|KASAN|STACKPROTECTOR|RKP|UH_RKP|KDP|CFP)=' "$G/out/.config"
