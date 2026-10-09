#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src/core"
echo "=== binwrite_target uses ==="
grep -rn "binwrite_target" "$G"
echo
echo "=== page_base out-of-page-ish refs (PHYSRW/UMH offsets) ==="
grep -rn -e "page_base +" -e "page_base+" "$G" | grep -v "//" | head -40
