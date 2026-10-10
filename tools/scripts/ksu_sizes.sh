#!/bin/bash
K=/root/ghostlock/_ksu
R=/root/ghostlock/src/g9700
echo "==BakaSU top=="
ls -la "$K" | head -30
echo "==du kernel/userspace=="
du -sh "$K/kernel" "$K/userspace" "$K/manager" 2>&1
echo "==userspace=="
ls -la "$K/userspace" 2>&1
ls -la "$K/userspace/ksud" 2>&1 | head
echo "==ROM configs=="
ls -la "$R/out/.config" 2>&1
ls -la "$R/arch/arm64/configs" 2>&1 | grep -i beyond
ls -la "$R/build_kernel.sh" 2>&1
echo "==kernel syms=="
ls -la /root/ghostlock/kernel/ 2>&1
