#!/bin/bash
cd ~/ghostlock || exit 1
echo "=== futex symbols ==="
grep -i futex kernel/kallsyms_fixed.txt
echo
echo "=== section symbols ==="
grep -E ' (_stext|_etext|_sinittext|_einittext|__init_begin|__init_end|_text|__bss_start|__bss_stop|_end)$' kernel/kallsyms_fixed.txt
echo
echo "=== disasm __arm64_sys_futex (find its bl target) ==="
K=kernel/vmlinux.elf; T=0x3594000
OFF=$(grep -E ' __arm64_sys_futex$' kernel/kallsyms_fixed.txt | awk '{print $1}')
echo "sym off=0x$OFF"
if [ -n "$OFF" ]; then
  A=$((T + 0x$OFF)); E=$((A + 0x60))
  aarch64-linux-gnu-objdump -d --start-address=$A --stop-address=$E $K 2>/dev/null | sed -n '6,40p'
fi
