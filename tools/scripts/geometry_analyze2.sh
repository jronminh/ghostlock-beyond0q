#!/bin/bash
cd ~/ghostlock || exit 1
show() {
  local name=$1 off=$2 span=${3:-0x50}
  local A=$((off)); local E=$((off+span))
  echo "===== $name (file off 0x$(printf %x $off)) ====="
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image --start-address=$A --stop-address=$E 2>/dev/null | sed -n '6,34p'
  echo
}
show do_futex        0xf11dc 0x30
show SyS_futex       0xf507c 0x40
show core_sys_select 0x228e3c 0x30
show SyS_select      0x229894 0x40
show SyS_pselect6    0x229a5c 0x40
