#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
git add docs/KSU_ROOT_FINDINGS.md probe_root.sh
git commit -q -m "docs+test: what full root looks like (probe_root.sh)

uid=0 + full caps + kernel ctx; reads root-only dirs; getenforce=Permissive.
Limitation: creating NEW /data files fails -ENOKEY (fscrypt keyring); writing
existing (warmed) files works. /proc/kallsyms addrs hashed even as root."
git log --oneline -2
