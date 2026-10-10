#!/bin/bash
S=/root/ghostlock/src/g9700
K=/root/ghostlock/kernel/kallsyms_fixed.txt
echo "=== [1] CODE WRITE: set_memory_rw / page tables / RKP guard ==="
grep -rn "set_memory_rw\|set_memory_ro\|__set_fixmap\|change_memory_common" "$S/arch/arm64/mm" 2>/dev/null | grep -v '\.o:' | head -12
echo "-- rkp symbols tying to pgd/dmap --"
grep -iE 'rkp_assign_pgd|rkp_prot|dmap|kdp_|rkp_ro_alloc|security_integrity' "$K" | head -20
echo "-- rkp source locations --"
find "$S" -type d -iname '*rkp*' 2>/dev/null | head
find "$S" -type f \( -iname '*rkp*.c' -o -iname '*rkp*.h' \) 2>/dev/null | head
echo
echo "=== [2] DEFEX: enforcement + gates ==="
grep -rn "int task_defex_enforce\|task_defex_enforce\|defex_enforce\|DEFEX_FEATURE\|defex_get_features\|enforce" "$S/security/defex_lsm/" 2>/dev/null | grep -v '\.o:' | head -25
echo
echo "=== [3] MODULE HOOK surface (KernelSU) ==="
grep -wE '__arm64_sys_setuid|sys_call_table|kallsyms_lookup_name|register_kprobe|sys_call_table' "$K" | head
echo "-- binfmt/kprobe configs --"
grep -E 'CONFIG_KPROBES|CONFIG_KRETPROBES|CONFIG_HAVE_KPROBES|CONFIG_BPF|CONFIG_MODULES' "$S/out/.config"
echo
echo "=== [4] DM-VERITY / FIVE hooks ==="
grep -iE 'five_is_dmverity_protected|dm_verity|five_verify' "$K" | head
grep -rn "CONFIG_DM_VERITY_AVB\|CONFIG_FIVE\|CONFIG_DM_VERITY_FEC" "$S/out/.config"
