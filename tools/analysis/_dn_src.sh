#!/bin/bash
set -e
echo "=== src tree top ==="
ls -la "$HOME/ghostlock/src"
echo "=== g970w ==="
find "$HOME/ghostlock/src/g970w" -maxdepth 2 | head -40
echo "=== g9700 top ==="
find "$HOME/ghostlock/src/g9700" -maxdepth 1 | head -40
echo "=== find configfs/file.c ==="
find "$HOME/ghostlock/src" -path '*configfs/file.c' 2>/dev/null
echo "=== find slub.c / mm_types.h / slab_def.h ==="
find "$HOME/ghostlock/src" -name 'slub.c' -o -name 'mm_types.h' -o -name 'slab_def.h' -o -name 'page-flags.h' 2>/dev/null | head
