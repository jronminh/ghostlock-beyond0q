#!/bin/bash
cd ~/ghostlock || exit 1
K=kernel/vmlinux.elf
echo "===== _text (0x3594000) first 24 insns ====="
aarch64-linux-gnu-objdump -d --start-address=0x3594000 --stop-address=0x3594100 $K 2>/dev/null | sed -n '6,30p'
echo
echo "===== do_futex (0x368516c) first 40 insns ====="
aarch64-linux-gnu-objdump -d --start-address=0x368516c --stop-address=0x3685280 $K 2>/dev/null | sed -n '6,50p'
echo
echo "===== vmlinux-to-elf help ====="
vmlinux-to-elf --help 2>&1 | head -30
echo
echo "===== kallsyms-finder present? ====="
ls /usr/local/lib/python3*/dist-packages/vmlinux_to_elf/scripts/ 2>/dev/null || python3 -c "import vmlinux_to_elf, os; print(os.path.dirname(vmlinux_to_elf.__file__))"
