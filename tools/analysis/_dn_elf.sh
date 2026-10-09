#!/bin/bash
echo "=== find vmlinux/btf/system.map/System.map artifacts ==="
find "$HOME/ghostlock" -maxdepth 3 -type f \( -iname '*btf*' -o -iname '*system.map*' -o -iname 'vmlinux*' -o -iname '*.config' \) -printf '%s  %p\n' 2>/dev/null | head -40
echo
echo "=== ELF section headers (kernel) ==="
readelf -SW "$HOME/ghostlock/kernel/vmlinux.elf" | head -30
echo
echo "=== ELF program headers ==="
readelf -lW "$HOME/ghostlock/kernel/vmlinux.elf" | head -40
