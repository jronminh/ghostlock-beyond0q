# Runtime physical access via a dirty user PTE (and the KDP write wall)

Status: **verified on-device** (SM-G970W, 4.14.190-abG970WVLU9IXE1).  Companion to
`docs/KGSL_CVE_2023_21665.md` (the GPU-DMA primitive) and `docs/RKP_REFERENCES.md`.

Implemented as the `PTEMAP` / `PTEWRITE` hook in `src/core/fops.c`.

## What it does

Using the arbitrary kernel R/W we already have (the configfs gadget), `PTEMAP=1`
remaps a chosen physical page into the calling process's address space by editing
one of our own PTEs.  Result: **userspace arbitrary-physical read** (and write, where
allowed).

Discovery is done at runtime and self-verified (no speculative writes):

* find our `task_struct` by walking `init_task.tasks` and matching `pid`;
* find `mm` and `mm->pgd` by scanning `task+0x200..0x1200` for a direct-map pointer
  whose page-aligned `pgd` field walks a known user VA to the expected `struct page`
  (verified by reading the page's linear-map alias).

Offsets found on this device (the tree's `task_struct`/`mm_struct` do **not** match
the shipping kernel):

* `task->mm`            = `task + 0x5f8`
* `mm->pgd`             = `mm + 0x48`
* page-table levels: **3** (VA_BITS=39, 4K granule): shifts `{30,21,12}`
* `PHYS_OFFSET` (`memstart_addr`, readable from `.rodata`) = `0x80000000`
* `kimage_voffset` (readable) = `VA(image) - phys(image)`

Important arm64 detail: **page-table descriptors hold *physical* addresses of the
next-level table.**  Software walking must convert each descriptor's OA to a kernel
VA with `__va()` = `(oa - PHYS_OFFSET) | PAGE_OFFSET` before dereferencing it (the
kernel does this via `pgd_page_vaddr()`/`pud_offset()` etc.).  Our first attempts
failed (stage "invalid level-1 descriptor") purely because of this.

To install a mapping:

1. `mmap` two anonymous pages `va1`, `va2` and fault both in;
2. read `va1`'s PTE (gives a known-good user page descriptor + its phys);
3. `mprotect(va2, PROT_NONE)` — this flushes the TLB entry for `va2`;
4. write `(va1_pte & ~OA_MASK) | target_phys` into `va2`'s PTE slot;
5. access `va2` — now aliases the chosen physical page.

`PTEMAP=<hex>` reads 32 bytes; `PTEMAP=banner` targets `linux_banner`/rodata;
`PTEWRITE=<byte>` writes one byte at the same offset.

### Verified

```
ptemap: FOUND mm_off=5f8 pgd_off=48 mm=ffffffc1eb8bcd00 pgd=ffffffc0318ea000 ms=80000000 lv=3
ptemap: phys=0000000080000000 pte=00e8000080000f53 reading va2...
ptemap: read = 71 00 79 fb 00 00 0c 0d ...        # raw phys 0x80000000
```

Reading kernel **`.rodata`** from userspace works and the device stays up:

```
ptemap: va=ffffff80099800d2 phys=0000000081980000 off=d2
ptemap: read = 25 73 20 76 65 72 73 69 6f 6e 20 25 73 ... |%s version %s (dpi@SWDK6011) (cl|
```

That page is mapped read-only by the kernel, yet our user mapping reads it:
**the kernel's RO permission is per-mapping, not per-frame.**

## The wall: writing kernel-image pages halts the device (KDP/RKP stage-2)

Writing one byte into the **same** `.rodata` page (`PTEMAP=… PTEWRITE=0x56`):

```
ptemap: read = 76 65 72 73 69 6f 6e ...
   <dead>   # no "WRITE" line, no "PTE restored", no Oops, no panic, no reset reason
```

The device goes silent **at the store instruction**.  `/proc/version` after the
following reboot is unchanged.

Interpretation: this is **not** a periodic scan/hash (that would let the store
complete and at least print the `WRITE` line).  It is an immediate trap to EL2:
the kernel-image physical pages are write-protected in **stage-2** by RKP/KDP, so
EL0 (or EL1) writes through *any* stage-1 mapping take a stage-2 fault that the
secure monitor treats as a violation and **halts** the SoC (hence no EL1 Oops and
no reset-reason entry).  Reads are allowed in stage-2, which is why reading works.

Consequences for "runtime ROM tweaking":

* CPU-side writes to `.text`/`.rodata` are **not** reachable (dirty-PTE or any other
  mapping cannot beat a stage-2 write ban).
* CPU-side writes to unprotected physical memory (kernel `.data`/`.bss`, slab, page
  tables, user pages) **do** work — the existing arbitrary VA write already covers
  these, and the dirty-PTE mapping additionally lets us *read* arbitrary physical
  pages (including protected ones).

### Gotcha: always restore the crafted PTE

Leaving the crafted PTE in place makes `zap_pte_range()` at process exit call
`put_page()` on a page we do not own -> refcount corruption -> hard hang (again, no
panic).  Always write the original PTE value back before returning (the code does,
and prints `PTE restored`).

## Next

1. Use the **GPU-DMA** primitive (`docs/KGSL_CVE_2023_21665.md`) to write the same
   `.rodata` page through the *device* path (SMMU stage-2 is programmed by Linux
   `dma_map_sg`, not by the secure monitor) and see whether a device write is also
   trapped — the open question for patching protected kernel image pages.
2. Boundary the stage-2 ban: which kernel-image ranges are write-protected
   (`.text`/`.rodata` only?) vs. readable/writable.
3. For persistent "ROM" changes, target the on-disk partitions (root via the
   safeplace bind-mount), which is unaffected by stage-2.
