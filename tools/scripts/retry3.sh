#!/bin/bash
cd ~/ghostlock || exit 1
vmlinux-to-elf --use-absolute kernel/Image kernel/vmlinux3.elf 2>&1 | tail -4
echo "=== check ==="
aarch64-linux-gnu-nm -n kernel/vmlinux3.elf 2>/dev/null | awk 'NF>=3{print $1" "$2" "$3}' > kernel/kallsyms3.txt
grep -E ' (_text|do_futex|core_sys_select)$' kernel/kallsyms3.txt
A=$(grep -E ' do_futex$' kernel/kallsyms3.txt | awk '{print $1}')
echo "do_futex @ 0x$A"
aarch64-linux-gnu-objdump -d --start-address=0x$A --stop-address=$((0x$A + 0x60)) kernel/vmlinux3.elf 2>/dev/null | sed -n '6,22p'
