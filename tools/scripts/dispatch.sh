#!/bin/bash
cd ~/ghostlock || exit 1
echo "=== symbols === "
grep -E ' (el0_svc|el0_svc_handler|el0_svc_common|invoke_syscall|do_syscall|syscall_trace_enter|__arm64_sys_futex)$' kernel/kallsyms_fixed.txt
echo
for s in el0_svc_handler invoke_syscall; do
  A=$(grep -E " $s\$" kernel/kallsyms_fixed.txt | awk '{print $1}')
  [ -z "$A" ] && { echo "$s: not found"; continue; }
  O=$(( (0x$A) - 0xffffff8008000000 ))
  echo "===== $s (off 0x$(printf %x $O)) ====="
  aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 kernel/Image \
    --start-address=$O --stop-address=$((O+0xa0)) 2>/dev/null | sed -n '6,40p'
  echo
done
