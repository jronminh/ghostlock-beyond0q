#!/bin/bash
cd ~/ghostlock/src/g9700 || exit 1
echo "=== stub secgetspf + python2 ==="
printf '#!/bin/sh\nexit 0\n' | sudo tee /usr/local/bin/secgetspf >/dev/null
sudo chmod +x /usr/local/bin/secgetspf
sudo ln -sf /usr/bin/python3 /usr/local/bin/python2 2>/dev/null
command -v secgetspf; command -v python2
echo
echo "=== what does bounds.s compile look like (Kbuild:22) ==="
sed -n '18,26p' Kbuild
echo
echo "=== find CC wrapper / REAL_CC settings ==="
grep -n 'REAL_CC\|^CC\s*=\|CROSS_COMPILE\|real-cc\|cc-wrapper\|--target=' Makefile | head -20
echo
echo "=== retry prepare ==="
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make O=out prepare 2>&1 | grep -v 'python2: No such' | tail -30
