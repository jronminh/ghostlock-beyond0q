#!/bin/bash
echo "=== ghostlock dir ==="
ls -la "$HOME/ghostlock" | head -30
echo
echo "=== ap/ ==="
ls -la "$HOME/ghostlock/ap" 2>/dev/null | head -20
echo
echo "=== any AP tar / firmware ==="
find "$HOME/ghostlock" -maxdepth 2 -iname 'AP*' -o -maxdepth 2 -iname '*G970W*' 2>/dev/null | head -20
echo
echo "=== bl_dec / kernel dirs ==="
ls "$HOME/ghostlock/bl_dec" 2>/dev/null | head
