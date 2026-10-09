#!/bin/bash
cd ~/ghostlock || exit 1
echo "=== do_futex: usages of x28 and rt_mutex calls (0xf11dc..0xf1600) ==="
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0xf11dc --stop-address=0xf1600 2>/dev/null | grep -nE 'x28|rt_mutex|spin_lock|plist|bl ' | head -50
echo
echo "=== confirm the 0xd0 add context ==="
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0xf1250 --stop-address=0xf12d0 2>/dev/null | sed -n '6,40p'
