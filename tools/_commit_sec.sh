#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add docs/KSU_ROOT_FINDINGS.md readpersist.sh readparam.sh
git commit -q -m "docs: Samsung protection stack vs root (RKP/DEFEX/FIVE/verity/TEE)

Survey of CONFIG_RKP_*, DEFEX, FIVE, dm-verity, MODULE_SIG, STRICT_KERNEL_RWX and
device state (verifiedbootstate=green, vbmeta locked, oem_unlock_allowed=0).
Observed RKP CRED PROTECTION VIOLATION panic (security_integrity_current) after
cred repoint -> cred/page-table edits are off-limits. Bootloader unlock infeasible
at runtime (obfuscated persistent, no plaintext OEM/KG in param). Persistence is
therefore per-boot only."
git log --oneline -2
