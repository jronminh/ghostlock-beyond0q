#!/bin/bash
cd ~/ghostlock/src || exit 1
echo "=== nproc / mem ==="
nproc; free -h | head -2
echo
echo "=== overlay G970W onto G9700 ==="
cp -rf g970w/Kernel/. g9700/
echo "done"
cd g9700
echo "=== beyond0 defconfigs ==="
ls arch/arm64/configs | grep -i beyond0
echo
echo "=== Makefile head (kernel version) ==="
head -5 Makefile
echo
echo "=== toolchain present? ==="
for t in aarch64-linux-gnu-gcc clang; do printf "%-24s " $t; command -v $t || echo MISSING; done
clang --version 2>/dev/null | head -1
