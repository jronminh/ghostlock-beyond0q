#!/bin/bash
V=/root/ghostlock/kernel/vmlinux.elf
echo "==file=="
file "$V"
echo "==nm sig_enforce / sig=="
aarch64-linux-gnu-nm "$V" 2>/dev/null | grep -iE 'sig_enforce|module_sig_check|mod_verify_sig' | head
echo "==nm count=="
aarch64-linux-gnu-nm "$V" 2>/dev/null | wc -l
echo "==readelf syms=="
aarch64-linux-gnu-readelf -sW "$V" 2>/dev/null | grep -iE 'sig_enforce' | head
echo "==kallsyms files search=="
grep -i 'sig_enforce' /root/ghostlock/kernel/kallsyms*.txt 2>/dev/null | head
echo "==sections=="
aarch64-linux-gnu-readelf -SW "$V" 2>/dev/null | grep -E '\.data|\.bss|ksymtab|kcrctab|symtab' | head -20
