#!/bin/bash
echo "=== out/ tree (depth 3) ==="
find "$HOME/ghostlock/src/g9700/out" -maxdepth 3 -printf '%y %10s %p\n' 2>/dev/null | head -60
echo
echo "=== any System.map / vmlinux / .config / autoconf under g9700 ==="
find "$HOME/ghostlock/src/g9700" -maxdepth 5 \( -name 'System.map' -o -name 'vmlinux' -o -name 'vmlinux.o' -o -name '.config' -o -name 'autoconf.h' -o -name 'utsrelease.h' \) -printf '%10s %p\n' 2>/dev/null | head -30
echo
echo "=== kernel version from Makefile ==="
head -5 "$HOME/ghostlock/src/g9700/Makefile"
