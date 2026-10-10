#!/bin/bash
S=/root/ghostlock/src/g9700
O=$S/out
H=/root/ghostlock/hello
rm -rf "$H"; mkdir -p "$H"
cat > "$H/hello.c" <<'EOF'
#include <linux/module.h>
#include <linux/kernel.h>
static int __init hello_init(void) { pr_info("gl-hello: loaded\n"); return 0; }
static void __exit hello_exit(void) { pr_info("gl-hello: unloaded\n"); }
module_init(hello_init);
module_exit(hello_exit);
MODULE_LICENSE("GPL");
EOF
cat > "$H/Makefile" <<'EOF'
obj-m := hello.o
EOF
echo "==build hello.ko=="
make -C "$S" O="$O" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  CC=aarch64-linux-gnu-gcc M="$H" modules 2>&1 | tail -25
echo "rc=${PIPESTATUS[0]}"
echo "==result=="
ls -la "$H"/*.ko 2>&1
echo "==modinfo=="
aarch64-linux-gnu-objdump -h "$H/hello.ko" 2>/dev/null | grep -E 'module_sig|gnu.linkonce|versions|vermagic' 
echo "==vermagic string in ko=="
strings "$H/hello.ko" 2>/dev/null | grep -i "4.14" | head
