#!/bin/bash
cd ~/ghostlock || exit 1
K=kernel/vmlinux.elf
T=0x3594000
show() {
  local name=$1 off=$2 span=$3
  local A=$((T + off)); local E=$((A + span))
  echo "===== $name  (off 0x$(printf %x $off)) ====="
  aarch64-linux-gnu-objdump -d --start-address=$A --stop-address=$E $K 2>/dev/null | sed -n '6,60p'
  echo
}
show do_futex 0xef074 0x120
show remove_waiter 0xb2064 0xc0
show core_sys_select 0x224e2c 0x140
