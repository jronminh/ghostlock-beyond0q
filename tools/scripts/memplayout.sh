#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus
echo "=== target.h memory layout ==="
grep -nE 'DIRECT_MAP|VMEMMAP|STRUCT_PAGE|P0_PAGE_OFFSET|P0_PHYS_OFFSET|P0_KERNEL_PHYS|KERNELSNITCH_IDENTITY|KIMAGE_TEXT_BASE' src/core/target.h
echo
echo "=== 4.14 source: VMEMMAP_SIZE / direct map / struct page ==="
F=/root/ghostlock/src/g9700/arch/arm64/include/asm/memory.h
grep -nE 'VMEMMAP_SIZE|VMEMMAP_START|DIRECT_MAP|struct page|STRUCT_PAGE' "$F" | head
echo "--- VMEMMAP_SIZE def ---"
sed -n '/define VMEMMAP_SIZE/,+6p' "$F"
echo
echo "=== config: page shift / struct page size ==="
grep -E 'CONFIG_ARM64_PAGE_SHIFT|CONFIG_ARM64_VA_BITS|CONFIG_ZONE_DEVICE|CONFIG_SPARSEMEM_VMEMMAP|CONFIG_ARM64_64K_PAGES' /root/ghostlock/src/g9700/out/.config 2>/dev/null
echo "=== struct page size in 4.14? (include/linux/mm_types.h) ==="
grep -nE 'struct page \{|_struct_page_alignment|CONFIG_HAVE_ALIGNED_STRUCT_PAGE' /root/ghostlock/src/g9700/include/linux/mm_types.h | head
