#!/bin/bash
cd ~/ghostlock || exit 1
cp -f /mnt/e/Library/Desktop/ghostlock/trigger.c .
echo "=== build static arm64 ==="
aarch64-linux-gnu-gcc -static -O2 -pthread trigger.c -o /mnt/e/Library/Desktop/ghostlock/trigger_a64 2>&1
file /mnt/e/Library/Desktop/ghostlock/trigger_a64
ls -l /mnt/e/Library/Desktop/ghostlock/trigger_a64
