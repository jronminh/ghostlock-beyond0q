#!/bin/bash
S=/root/ghostlock/src/g9700
echo "== include/linux/rkp.h =="
cat "$S/include/linux/rkp.h" 2>&1
echo
echo "== arch/arm64/include/asm/rkp_cfp.h (head) =="
head -80 "$S/arch/arm64/include/asm/rkp_cfp.h" 2>&1
echo
echo "== drivers/uh (rkp) =="
ls "$S/drivers/uh" 2>&1
echo "== grep KDP / protected regions =="
grep -rniE 'kdp|protected|region|dmabuf|pgd|ropp|jopp|cfp' "$S/include/linux/rkp.h" "$S/arch/arm64/kernel/rkp_cfp.c" 2>/dev/null | head -40
