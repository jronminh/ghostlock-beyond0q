#!/bin/bash
IMG=/root/ghostlock/kernel/Image
BASE=0xffffff8008000000
K=/root/ghostlock/kernel
echo "###### task_struct: usage offset via put_task_struct / get_task_struct ######"
grep -nE ' (__put_task_struct|put_task_struct|get_task_struct|free_task)$' $K/kallsyms_fixed.txt
PUT=$(grep -nE ' __put_task_struct$' $K/kallsyms_fixed.txt | head -1 | cut -d: -f2 | cut -c1-16)
echo "--- __put_task_struct @ 0x$PUT (find atomic_dec on usage) ---"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
  --start-address=0x$PUT --stop-address=$((0x$PUT+0x80)) | sed -n '6,40p'
echo
echo "###### CANDIDATES: any 'ldr w, [x0, #imm]' with imm 0x10..0x40 in _do_fork/dup_task_struct? ######"
DT=$(grep -nE ' dup_task_struct$' $K/kallsyms_fixed.txt | head -1 | cut -d: -f2 | cut -c1-16)
echo "dup_task_struct @ 0x$DT"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=$BASE "$IMG" \
  --start-address=0x$DT --stop-address=$((0x$DT+0x160)) | grep -nE 'str\s+w[0-9]+, \[x[0-9]+, #0x(10|18|20|28|30|38|40)\]|ldr\s+w[0-9]+, \[x[0-9]+, #0x(10|18|20|28|30|38|40)\]' | head -20
