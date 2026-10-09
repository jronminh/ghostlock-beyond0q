#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
D() { aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
      --start-address=$1 --stop-address=$2 | sed -n '6,260p'; }
echo "===== compat_SyS_select 0xffffff800822a20c ====="
D 0xffffff800822a20c 0xffffff800822a2ac
echo
echo "===== compat_core_sys_select 0xffffff800822b59c ====="
D 0xffffff800822b59c 0xffffff800822b780
