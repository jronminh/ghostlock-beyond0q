#!/bin/bash
cd ~/ghostlock/src || exit 1
echo "=== overlay Kconfig content ==="
cat -A g970w/Kernel/arch/arm64/Kconfig | head -60
echo
echo "=== overlay tree (all files) ==="
find g970w/Kernel -type f | sed 's#g970w/Kernel/##' | sort
echo
echo "=== extract ORIGINAL arch/arm64/Kconfig ==="
cd orig
tar -xzf Kernel.tar.gz --wildcards '*arch/arm64/Kconfig' 2>&1 | head
find . -name Kconfig | head
ls -la arch/arm64/Kconfig 2>/dev/null || ls -la ./arch/arm64/Kconfig 2>/dev/null
