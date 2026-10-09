#!/bin/bash
cd ~/ghostlock || exit 1
pip3 install --break-system-packages -q -U vmlinux-to-elf 2>&1 | tail -2
echo "=== rerun ==="
vmlinux-to-elf kernel/Image kernel/vmlinux2.elf 2>&1 | tail -8
echo "=== symbol check: do_futex / core_sys_select / futex_wait ==="
aarch64-linux-gnu-nm -n kernel/vmlinux2.elf 2>/dev/null | awk 'NF>=3{print $1" "$2" "$3}' > kernel/kallsyms2.txt
grep -E ' (_text|do_futex|futex_wait|futex_requeue|futex_wait_requeue_pi|core_sys_select|do_select|compat_do_futex)$' kernel/kallsyms2.txt
echo "=== does the function at do_futex look like futex syscall? (first 25) ==="
A=$(grep -E ' do_futex$' kernel/kallsyms2.txt | awk '{print $1}')
echo "do_futex @ 0x$A"
aarch64-linux-gnu-objdump -d --start-address=0x$A --stop-address=$((0x$A + 0xc0)) kernel/vmlinux2.elf 2>/dev/null | sed -n '6,32p'
