#!/bin/bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-pip binutils-aarch64-linux-gnu >/dev/null 2>&1
pip3 install --break-system-packages -q capstone 2>/dev/null || pip3 install -q capstone 2>/dev/null
echo "=== verify toolchain ==="
aarch64-linux-gnu-objdump --version 2>/dev/null | head -1
aarch64-linux-gnu-readelf --version 2>/dev/null | head -1
python3 -c "import capstone; print('capstone', capstone.__version__)" 2>&1
echo "=== tools/lz4 sanity ==="
lz4 --version 2>&1 | head -1
