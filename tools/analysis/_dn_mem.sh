#!/bin/bash
G="$HOME/ghostlock/src/g9700"
echo "=== arm64 memory.h VMEMMAP / PAGE_OFFSET ==="
grep -n -e "VMEMMAP_START" -e "define PAGE_OFFSET" -e "VA_BITS" -e "vmemmap" "$G/arch/arm64/include/asm/memory.h" "$G/arch/arm64/include/asm/pgtable.h" 2>/dev/null | head -30
echo
echo "=== generated asm/memory.h? ==="
ls "$G/out/arch/arm64/include/generated/asm/" 2>/dev/null | head
echo
echo "=== config zone dma / va bits ==="
grep -E 'CONFIG_(ZONE_DMA|ARM64_VA_BITS|SPARSEMEM_VMEMMAP|ARM64_4K_PAGES|NR_CPUS|MAX_ORDER|SLUB_CPU_PARTIAL|DEBUG_SPINLOCK|LOCKDEP|PREEMPT)=' "$G/out/.config"
echo
echo "=== useful symbol offsets ==="
grep -E ' (__per_cpu_offset|kmalloc_caches|anon_pipe_buf_ops|init_task|init_cred|system_unbound_wq|call_usermodehelper_exec_work)$' "$HOME/ghostlock/kernel/kallsyms_fixed.txt"
