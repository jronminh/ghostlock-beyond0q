#!/bin/bash
set -e
echo "=== installing tools ==="
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq lz4 unzip python3 binutils file vim-common >/dev/null
echo "=== verify ==="
for t in unzip lz4 python3 objdump readelf file xxd; do
  if command -v "$t" >/dev/null 2>&1; then echo "OK   $t"; else echo "MISS $t"; fi
done
echo "=== workspace ==="
mkdir -p ~/ghostlock
cd ~/ghostlock
cp -f "/mnt/e/Library/Desktop/BL_G970WVLU9IXE1_G970WVLU9IXE1_MQB80365760_REV00_user_low_ship_MULTI_CERT.tar.md5.zip" ./bl.zip
ls -la
echo "=== unzip ==="
unzip -o bl.zip
ls -la
