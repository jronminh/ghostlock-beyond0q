#!/bin/bash
set -e
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
# sanity: confirm KSU_ROOT_FINDINGS is English-ish (show any matched non-ascii)
echo "== suspicious chars in KSU_ROOT_FINDINGS =="
grep -oP '[\x{00C0}-\x{1EF9}]' docs/KSU_ROOT_FINDINGS.md 2>/dev/null | sort -u | head

DROP="docs/AUDIT_GEOMETRY.md docs/AUDIT_PHIEN5.md docs/BAN_GIAO.md docs/BAN_GIAO_PHIEN4.md \
docs/_dn_init_hooks.md docs/_dn_session4.md docs/FLOW.md docs/HANDOFF.md docs/KET_LUAN_4.14.md \
docs/PANIC_CAUSE.md docs/PHIEN_2026-10-10.md docs/PORT_4.14.md docs/PROMPT_PHIEN_3.md \
docs/PROMPT_PHIEN_4.md docs/PROMPT_PHIEN_5.md docs/SESSION_RECOVERY.md docs/TONG_QUAN.md"
for f in $DROP; do git rm -q --ignore-unmatch "$f"; done
echo "== remaining docs =="
ls docs
