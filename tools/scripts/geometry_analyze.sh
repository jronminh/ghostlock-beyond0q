#!/bin/bash
cd ~/ghostlock || exit 1
echo "=== symbols ==="
grep -E ' (SyS_select|SyS_futex|SyS_pselect6|core_sys_select|do_futex|SyS_epoll_wait|SyS_poll)$' kernel/kallsyms_fixed.txt
echo
show() {
  local name=$1 span=${2:-0x60}
  local A=$(grep -E " $name\$" kernel/kallsyms_fixed.txt | awk '{print $1}')
  [ -z "$A" ] && { echo "$name: not found"; return; }
  local O=$((0x$A)); local E=$((O+span))
  echo "===== $name (off 0x$(printf %x $O)) ====="
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image --start-address=$O --stop-address=$E 2>/dev/null | sed -n '6,40p'
  echo
}
show SyS_select 0x60
show SyS_futex 0x60
show SyS_pselect6 0x60
