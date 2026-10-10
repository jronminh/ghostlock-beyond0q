#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add docs/KSU_ROOT_FINDINGS.md
git commit -q -m "docs: RKP internals (kdp_init offsets, page-table ownership, CFP) + security hardware

RKP is TZ firmware driven by SMC; it owns/shadows the kernel page tables and is
handed the offsets of cred fields, task->cred, .text/.rodata ranges, page-table
bitmaps and selinux state. Explains why cred/text/page-table edits panic
(security_integrity_current) while plain .data writes (modprobe_path et al) do not.
Hardware: TEE + Qualcomm SPU + eSE; no discrete Knox Vault on S10e."
git log --oneline -2
