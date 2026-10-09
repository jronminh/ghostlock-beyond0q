#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
echo "=== lines starting with space (glitch) ==="
grep -nP '^ ' arch/arm64/Kconfig | head
echo "count: $(grep -cP '^ ' arch/arm64/Kconfig)"
echo "=== fix leading spaces -> tab ==="
sed -i -E 's/^ +/\t/' arch/arm64/Kconfig
grep -nP '^ ' arch/arm64/Kconfig | head || true
echo "=== defconfig again ==="
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out beyond0qlte_can_single_defconfig 2>&1 | tail -12
