#!/bin/bash
S=/root/ghostlock/src/g9700
O=$S/out
echo "==CC/config=="
grep -E 'CONFIG_CC_IS|CONFIG_GCC_VERSION|CONFIG_CLANG_VERSION|CONFIG_LOCALVERSION|CONFIG_MODVERSIONS|CONFIG_MODULE_SIG' "$O/.config" 2>&1
echo "==Module.symvers?=="
ls -la "$O/Module.symvers" 2>&1
echo "==modules_prepare=="
make -s -C "$S" O="$O" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules_prepare 2>&1 | tail -25
echo "prepare_rc=${PIPESTATUS[0]}"
echo "==after=="
ls -la "$O/Module.symvers" "$O/include/generated/autoconf.h" 2>&1
