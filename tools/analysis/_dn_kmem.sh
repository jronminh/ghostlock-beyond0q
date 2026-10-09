#!/bin/bash
# Extract exact kernel struct offsets for SM-G970W 4.14.190 by compiling a probe
# with the tree's own generated config/headers, then reading the constant array
# from the emitted assembly.
set -e
G="$HOME/ghostlock/src/g9700"

cat > "$G/kernel/probe_kmem.c" <<'EOF'
#include <linux/mm.h>
#include <linux/slab.h>
#include <linux/slub_def.h>
#include <linux/gfp.h>

const unsigned long kmem_probe[] = {
	/* struct kmem_cache */
	offsetof(struct kmem_cache, cpu_slab),
	offsetof(struct kmem_cache, flags),
	offsetof(struct kmem_cache, min_partial),
	offsetof(struct kmem_cache, size),
	offsetof(struct kmem_cache, object_size),
	offsetof(struct kmem_cache, offset),
	offsetof(struct kmem_cache, cpu_partial),
	offsetof(struct kmem_cache, oo),
	offsetof(struct kmem_cache, max),
	offsetof(struct kmem_cache, min),
	offsetof(struct kmem_cache, allocflags),
	offsetof(struct kmem_cache, ctor),
	offsetof(struct kmem_cache, name),
	offsetof(struct kmem_cache, list),
	offsetof(struct kmem_cache, node),
	sizeof(struct kmem_cache),
	/* struct kmem_cache_cpu */
	offsetof(struct kmem_cache_cpu, freelist),
	offsetof(struct kmem_cache_cpu, tid),
	offsetof(struct kmem_cache_cpu, page),
	offsetof(struct kmem_cache_cpu, partial),
	sizeof(struct kmem_cache_cpu),
	/* struct page */
	offsetof(struct page, flags),
	offsetof(struct page, freelist),
	offsetof(struct page, slab_cache),
	offsetof(struct page, compound_head),
	offsetof(struct page, _mapcount),
	offsetof(struct page, _refcount),
	offsetof(struct page, lru),
	offsetof(struct page, private),
	sizeof(struct page),
	/* kmalloc cache layout */
	KMALLOC_SHIFT_HIGH,
	KMALLOC_NORMAL,
	KMALLOC_RECLAIM,
	NR_KMALLOC_TYPES,
	/* gfp flags sanity */
	GFP_KERNEL,
	__GFP_ACCOUNT,
};
EOF

cd "$G/out"
aarch64-linux-gnu-gcc -nostdinc -isystem /usr/lib/gcc-cross/aarch64-linux-gnu/14/include \
  -I../arch/arm64/include -I./arch/arm64/include/generated -I../include -I./include \
  -I../arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I../include/uapi \
  -I./include/generated/uapi -include ../include/linux/kconfig.h -I../kernel -Ikernel \
  -D__KERNEL__ -mlittle-endian -DKASAN_SHADOW_SCALE_SHIFT=3 -fno-strict-aliasing -fno-common \
  -fshort-wchar -std=gnu89 -fno-PIE -mgeneral-regs-only -DCONFIG_AS_LSE=1 \
  -fno-asynchronous-unwind-tables -mpc-relative-literal-loads -fno-pic -mabi=lp64 \
  -fno-delete-null-pointer-checks -O2 -fno-var-tracking-assignments -fno-jump-tables \
  -fno-strict-overflow -fno-merge-all-constants -fmerge-constants \
  -DKBUILD_BASENAME='"probe_kmem"' -DKBUILD_MODNAME='"probe_kmem"' \
  -S -o /tmp/probe_kmem.s ../kernel/probe_kmem.c
echo "gcc exit: $?"
echo "==================== .rodata ===================="
awk '/kmem_probe:/{f=1} f{print} /\.size.*kmem_probe/{if(f)exit}' /tmp/probe_kmem.s
