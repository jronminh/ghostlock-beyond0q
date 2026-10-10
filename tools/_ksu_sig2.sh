#!/bin/bash
V=/root/ghostlock/kernel/vmlinux.elf
echo "==strings sig_enforce=="
strings "$V" | grep -i "sig_enforce" | head
echo "==grep -abo enforce=="
grep -abo "enforce" "$V" | head
echo "==sections=="
aarch64-linux-gnu-readelf -SW "$V" 2>/dev/null | grep -E 'param|modinfo|ksymtab|kcrctab|\.data|\.rodata|\.bss'
echo "==nm sig/param=="
aarch64-linux-gnu-nm "$V" 2>/dev/null | grep -iE 'sig_|__param|param_' | head -40
