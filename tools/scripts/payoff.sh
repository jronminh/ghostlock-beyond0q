#!/bin/bash
cd ~/ghostlock || exit 1
echo "===== do_futex @ off 0xf11dc (raw Image) ====="
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --adjust-vma=0 \
  kernel/Image --start-address=0xf11dc --stop-address=0xf12e0 2>/dev/null | sed -n '6,45p'
echo
echo "===== extract_target.py (with FIXED kallsyms) ====="
python3 ghostlock-oneplus/tools/extract_target.py --kallsyms kernel/kallsyms_fixed.txt 2>&1 | head -90
