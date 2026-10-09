#!/bin/bash
cd ~/ghostlock || exit 1
rm -rf bl_dec && mkdir -p bl_dec
cd bl
for f in *.lz4; do
  lz4 -d -f "$f" "../bl_dec/${f%.lz4}" >/dev/null 2>&1 || echo "FAIL $f"
done
cd ../bl_dec
echo "=== decompressed ==="
ls -la
echo
echo "=== file types ==="
file *
