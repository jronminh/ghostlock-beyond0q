#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src/core"
echo "=== install_embedded_su ==="
grep -rn "install_embedded_su" "$G"
echo
echo "=== definition body ==="
for f in "$G"/*.c; do
  if grep -q "install_embedded_su" "$f"; then
    awk '/^int install_embedded_su/{f=1} f{print} f&&/^}/{exit}' "$f"
  fi
done
