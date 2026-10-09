#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
echo "=== install host deps ==="
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq bc flex bison libssl-dev libelf-dev zlib1g-dev >/dev/null 2>&1
echo "bc: $(command -v bc)  flex: $(command -v flex)  bison: $(command -v bison)"
echo
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
echo "=== prepare ==="
make O=out CC=aarch64-linux-gnu-gcc HOSTCC=gcc prepare 2>&1 | grep -v 'python2: No such' | tail -25
echo
echo "=== headers? ==="
ls -la out/include/generated/autoconf.h out/include/generated/bounds.h out/arch/arm64/include/generated/asm-offsets.h out/include/config/auto.conf 2>&1
