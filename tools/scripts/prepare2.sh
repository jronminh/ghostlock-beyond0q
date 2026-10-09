#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
echo "=== does gcc support the flag directly? ==="
aarch64-linux-gnu-gcc -fstack-protector-strong -c -x c /dev/null -o /dev/null && echo "gcc OK" || echo "gcc FAIL"
echo
echo "=== disable CC_STACKPROTECTOR in .config ==="
sed -i '/CONFIG_CC_STACKPROTECTOR/d' out/.config
printf 'CONFIG_CC_STACKPROTECTOR_NONE=y\n' >> out/.config
make O=out olddefconfig 2>&1 | tail -4
grep STACKPROTECTOR out/.config
echo
echo "=== prepare again ==="
make O=out prepare 2>&1 | grep -v 'python2' | tail -30
