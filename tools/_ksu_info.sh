#!/bin/bash
K=/root/ghostlock/_ksu
echo "==DOCS=="
ls -la "$K/docs" 2>&1
echo "==KERNEL=="
ls -la "$K/kernel" 2>&1 | head -50
echo "==JUSTFILE=="
sed -n '1,60p' "$K/justfile" 2>&1
echo "==SETUP?=="
find "$K" -maxdepth 2 -iname "setup.sh" -o -maxdepth 2 -iname "*.md" 2>/dev/null | head -40
echo "==BUILD DOC=="
for f in "$K/docs"/*.md; do echo "---- $f"; sed -n '1,60p' "$f"; done 2>&1 | head -200
