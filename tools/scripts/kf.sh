#!/bin/bash
cd ~/ghostlock || exit 1
KF=$(ls /usr/local/lib/python3*/dist-packages/vmlinux_to_elf/scripts/kallsyms_finder.py 2>/dev/null | head -1)
echo "finder: $KF"
python3 "$KF" kernel/Image > kernel/kallsyms_raw.txt 2> kernel/kallsyms_err.txt
echo "--- stderr ---"; head -20 kernel/kallsyms_err.txt
echo "--- lines ---"; wc -l kernel/kallsyms_raw.txt
echo "--- head ---"; head -5 kernel/kallsyms_raw.txt
echo "--- key ---"
grep -E ' (_text|_stext|do_futex|core_sys_select|futex_wait_requeue_pi|futex_requeue)$' kernel/kallsyms_raw.txt
echo "--- does 0x368516c still look like do_futex? show first line labeled do_futex ---"
grep -nE ' do_futex$' kernel/kallsyms_raw.txt
