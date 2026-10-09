#!/bin/bash
S=/mnt/e/Library/Desktop/ghostlock
R="$HOME/ghostlock/ghostlock-oneplus"
for f in BAN_GIAO_PHIEN4.md PROMPT_PHIEN_5.md _dn_session4.md _dn_init_hooks.md; do
  cp -f "$S/$f" "$R/$f"
done
ls -la "$R" | grep -E 'BAN_GIAO_PHIEN4|PROMPT_PHIEN_5|_dn_session4|_dn_init_hooks'
echo "---- git status ----"
git -C "$R" status --short
