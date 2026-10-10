# RKP image notes — this device's `hyp` (uH/RKP) binary

Companion to `docs/RKP_REFERENCES.md`. Everything here is **our own device**
(SM-G970W, Snapdragon 855 / msmnile, ROM 4.14.190) — not borrowed from other models.

## What we extracted

`/dev/block/by-name/hyp` → `/dev/block/sdd31`, size `2048` sectors = **1 MiB**.
Read with the kernel-domain root (`dd`) into a pre-created+warmed file, then `adb pull`.

```
ELF64 AArch64, type EXEC, entry 0x85710000, no section headers (stripped)
  LOAD  off 0x00003000  VA 0x85700000  filesz 0xf23d
  LOAD  off 0x00012240  VA 0x85710000  filesz 0x6f188  memsz 0x24c000   (RWE)
```

The image is the **uH micro-hypervisor + RKP "app"** (the two loadable segments); on
Snapdragon it lives in the `hyp` partition (loaded by QHEE — see the Compendium).

Layout: the two segments cover VA `0x85700000`–`0x8577f188`. **All 397 `RKP_` tokens sit
in segment 1** at file offset `0x10048`–`0x1222e` (VA ≈ `0x8570d048`–`0x8570f22e`) — that
compact block is the RKP **log/string table**. The image tail after `~0x82200` (≈0.5 MiB) is
high-entropy (a signature/blob), not code/strings.

## Log-string scheme (confirmed)

Log strings are not stored in clear; each **token** in a log string is replaced by
`RKP_<sha256(token)[:8]>`. Confirmed against our image:

```
sha256("rkp_paging.c")[:8] = b77f5327   and  our image contains "RKP_b77f5327"  ✓
```

So the placeholders are **recoverable by hashing a candidate dictionary**. Tool:
`scripts/rkp_hash.py <hyp.bin> <corpus...>` (dictionary = the Impalabs articles + kernel
source + wordlist). It prints `RKP_<hash> = token` for every match and writes the
unrecovered set to `tools/rkp_unrecovered.txt`. Our image has **368 unique placeholders**.

## Recovered source-file map (partial symbol map for *this* image)

```
rkp.c        rkp_init.c    rkp_kdp.c    rkp_paging.c
rkp_l1pgt.c  rkp_l2pgt.c   rkp_l3pgt.c
s2.c         sparsemap.c   pa_restrict.c  page_allocator.c
panic.c      general.c     event.c        main.c
```
(`rkp_l1pgt/l2pgt/l3pgt.c` = the stage-1 page-table processing, `rkp_paging.c`/`s2.c` =
stage-2 mapping, `rkp_kdp.c` = Kernel Data Protection, `pa_restrict.c` = protected ranges,
`sparsemap.c`/`page_allocator.c`/`pa_restrict.c` = uH control structures.)

## Recovered log strings (sample; 60/368 so far)

```
RKP Activated
CFP JOPP Enabled
CFP ROPP Enabled
Data Protection Violation
s2 change access not allowed after def-init
s2 range change access not allowed before init
Range change permission prohibited
Fail to change attribute to pxn
Fail to change attribute to rox
Failed to make Kernel range ROX
failed to make swapper_pg_dir RW
Failed to make executable for empty_zero_page
Fail alloc robitmap for kernel
Robuffer Free wrong address
out of memory
[*] uH fault handler has been registered
[+] uH initialized
[uH] PA Restrict Init
RKP is already started
EL1 doesn't support to get private sparsemap
Dynamic heap needs to be initialized
```
`CFP JOPP Enabled` / `CFP ROPP Enabled` = the **control-flow-integrity** layers are active on
this kernel (matches the "high-end US = JOPP+ROPP+KDP" matrix and our on-device RKP panics).
`Data Protection Violation` = the KDP violation path (the `cred` protection we tripped).

## Log templates

The raw templates (placeholders + preserved `%…` format specs) are in
`tools/rkp_templates.txt` (322 lines), e.g.:
```
RKP_02f32508 %lx, %p
%d RKP_78c4b47d
RKP_05e71c7f %pRKP_c5d4b9a4%xRKP_c5d4b9a4%xRKP_c5d4b9a4%x
```

## Next

1. Enlarge the dictionary (kernel tree, wordlists, more firmware from other Snapdragon
   units) to recover the remaining placeholders → fuller symbol map.
2. Disassemble `hyp.bin` (aarch64) around the recovered strings to locate
   `rkp_*` functions and the **RKP command handler table**, cross-mapped to the kernel-side
   IDs in `include/linux/rkp.h` (`RKP_WRITE_PGT1/2/3`, `RKP_NEW_PGD`, `RKP_JOPP_INIT`,
   `RKP_ROPP_*`, `RKP_MODULE_LOAD`, `RKP_FP_BPF_LOAD`, `RKP_KASLR_MEM`, `RKP_FIMC_VERIFY`).
