#!/bin/bash
cd ~/ghostlock || exit 1
# rt_mutex_start_proxy_lock off = 0xb3efc ; rt_mutex_adjust_prio_chain = 0xb2eec
echo "=== calls to rt_mutex_start_proxy_lock (b3efc) / adjust_prio_chain (b2eec) in do_futex ==="
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0xf11dc --stop-address=0xf2200 2>/dev/null | grep -nE 'bl .*(b3efc|b2eec)|add\s+x[0-9]+, sp, #0x' | head -60
echo
echo "=== context around the proxy_lock call ==="
L=$(aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0xf11dc --stop-address=0xf2200 2>/dev/null | grep -n 'b3efc' | head -1 | cut -d: -f1)
echo "line=$L"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
  --start-address=0xf11dc --stop-address=0xf2200 2>/dev/null | sed -n "$((L-14)),$((L+3))p"
