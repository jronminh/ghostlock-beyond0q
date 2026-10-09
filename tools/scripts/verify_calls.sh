#!/bin/bash
cd ~/ghostlock || exit 1
echo "=== SyS_futex: có bl thẳng tới do_futex (0xf11dc)? ==="
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0xf507c --stop-address=0xf52e0 2>/dev/null | grep -nE 'bl\s+0x'
echo
echo "=== SyS_select: có bl thẳng tới core_sys_select (0x228e3c)? ==="
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0x229894 --stop-address=0x229a5c 2>/dev/null | grep -nE 'bl\s+0x'
echo
echo "=== core_sys_select: xác nhận stack_fds = sp+0x50 (vùng dùng làm bits) ==="
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0x228e3c --stop-address=0x228f60 2>/dev/null | grep -nE 'sp, #0x|mov\s+x[0-9]+, x2[0-9]' | head -30
