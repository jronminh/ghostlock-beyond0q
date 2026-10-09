#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus
awk '/static int do_one_write/,/^}/' $R/src/core/main.c
echo "=== build ==="
bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlock53a 2>&1 | tail -2
cp -f /tmp/ghostlock53a /mnt/e/Library/Desktop/ghostlock/ghostlock53_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock53_a64
