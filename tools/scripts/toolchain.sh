#!/bin/bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gcc-aarch64-linux-gnu >/dev/null 2>&1
echo "=== toolchain ==="
aarch64-linux-gnu-gcc --version | head -1
echo "=== quick static test ==="
cat > /tmp/hello.c <<'EOF'
#include <stdio.h>
int main(){ printf("hi from arm64\n"); return 0; }
EOF
aarch64-linux-gnu-gcc -static -O2 /tmp/hello.c -o /tmp/hello_a64 && file /tmp/hello_a64
