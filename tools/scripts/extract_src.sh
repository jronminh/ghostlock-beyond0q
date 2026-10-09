#!/bin/bash
cd ~/ghostlock || exit 1
mkdir -p src && cd src
echo "=== outer unzip ==="
unzip -o /mnt/e/Library/Desktop/SM-G9700.zip >/dev/null
ls -la
echo
echo "=== G970W inner listing ==="
unzip -l SM-G970W_12_Opensource_*.zip 2>&1 | head -30
echo
echo "=== G9700 inner listing (top 25) ==="
unzip -l SM-G9700_12_Opensource.zip 2>&1 | head -25
echo "..."
unzip -l SM-G9700_12_Opensource.zip 2>&1 | tail -4
