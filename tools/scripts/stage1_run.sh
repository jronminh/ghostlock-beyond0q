#!/bin/bash
cd ~/ghostlock || exit 1
G=/mnt/e/Library/Desktop/ghostlock

echo "===== [1] vmlinux-to-elf ====="
vmlinux-to-elf kernel/Image kernel/vmlinux.elf 2>&1 | tail -20
ls -la kernel/vmlinux.elf 2>/dev/null || echo "NO ELF"

if [ -s kernel/vmlinux.elf ]; then
  echo "===== [2] kallsyms ====="
  aarch64-linux-gnu-nm -n kernel/vmlinux.elf 2>/dev/null | awk 'NF>=3{print $1" "$2" "$3}' > kernel/kallsyms.txt
  wc -l kernel/kallsyms.txt
  echo "--- key symbols ---"
  grep -E ' (_text|futex_wait_requeue_pi|core_sys_select|do_futex|futex_requeue|init_task|init_cred|selinux_state|kptr_restrict)$' kernel/kallsyms.txt

  echo "===== [3] extract_target.py ====="
  python3 ghostlock-oneplus/tools/extract_target.py --kallsyms kernel/kallsyms.txt 2>&1 | head -80
fi

echo "===== [4] check_feasibility.py ====="
python3 ghostlock-oneplus/tools/check_feasibility.py kernel/Image 2>&1 | head -120
