#!/bin/bash
echo "=== ensure /mnt/e mounted ==="
if ! ls /mnt/e/Library/Desktop >/dev/null 2>&1; then
  sudo mkdir -p /mnt/e
  sudo mount -t drvfs E: /mnt/e 2>&1
fi
ls /mnt/e/Library/Desktop | head -5
Z='/mnt/e/Library/Desktop/SM-G970W_4_20240521161810_5uyevxvdd4_fac.zip'
echo "=== zip listing ==="
unzip -l "$Z" | head -40
echo "=== free space ==="
df -h / /mnt/e 2>/dev/null
