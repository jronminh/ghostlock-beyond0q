#!/bin/bash
cd ~/ghostlock/src || exit 1
echo "=== overlay có arch/arm64/Kconfig không? ==="
ls -la g970w/Kernel/arch/arm64/Kconfig 2>&1
echo
echo "=== original Kconfig từ Kernel.tar.gz ==="
mkdir -p orig && cd orig
unzip -o ../SM-G9700_12_Opensource.zip Kernel.tar.gz >/dev/null
tar -xzf Kernel.tar.gz arch/arm64/Kconfig 2>/dev/null
ls -la arch/arm64/Kconfig
echo "--- diff orig vs current (g9700) ---"
diff arch/arm64/Kconfig ../g9700/arch/arm64/Kconfig | head -60
echo "--- lines 58-72 của ORIGINAL ---"
sed -n '58,72p' arch/arm64/Kconfig | cat -A
