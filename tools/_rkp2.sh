#!/bin/bash
S=/root/ghostlock/src/g9700
echo "== [a] RKP init callers (offsets handed to TZ) =="
grep -rn "rkp_init\|kdp_init\|RKP_START\|rkp_deferred_init\|rkp_started" "$S/arch/arm64" "$S/drivers/uh" 2>/dev/null | grep -v '\.o:' | head -30
echo
echo "== [b] page-table protection usage =="
grep -rn "rkp_is_pg_protected\|rkp_assign_pgd\|rkp_is_pg_dbl_mapped\|rkp_ro_alloc\|RKP_WRITE_PGT\|RKP_NEW_PGD" "$S/arch" "$S/mm" "$S/drivers/uh" 2>/dev/null | grep -v '\.o:' | head -30
echo
echo "== [c] set_memory_rw/ro implementation (does it consult RKP?) =="
sed -n '40,140p' "$S/arch/arm64/mm/pageattr.c"
echo
echo "== [d] CFP control-flow hook =="
grep -rn "ropp\|jopp\|sys_call_table\|RKP_CFP\|hook" "$S/arch/arm64/kernel/rkp_cfp.c" 2>/dev/null | head -25
