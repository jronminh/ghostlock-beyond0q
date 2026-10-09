#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
echo "=== restore original G9700 arch/arm64/Kconfig ==="
cp -f ../orig/arch/arm64/Kconfig arch/arm64/Kconfig
echo "config lines: $(grep -c '^config' arch/arm64/Kconfig)  size: $(stat -c%s arch/arm64/Kconfig)"
echo
echo "=== device .config from /proc/config.gz ==="
mkdir -p out
zcat /mnt/e/Library/Desktop/ghostlock/s10-config.gz > out/.config
echo "config lines: $(wc -l < out/.config)"
echo
echo "=== olddefconfig ==="
make O=out olddefconfig 2>&1 | tail -15
echo
echo "=== prepare ==="
make O=out prepare 2>&1 | tail -25
echo
echo "=== headers generated? ==="
ls -la out/include/generated/autoconf.h out/include/config/auto.conf 2>&1
