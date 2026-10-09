#!/bin/bash
cd /root/ghostlock/ghostlock-oneplus
echo "===== git log ====="
git log --oneline -8
echo
echo "===== git status (short) ====="
git status --short | head -30
echo
echo "===== ORIGINAL fops.c: prepare_pselect_fdsets + do_pselect_fake_lock_route ====="
git show HEAD:src/core/fops.c 2>/dev/null | sed -n '/void prepare_pselect_fdsets/,/^int repair_fake_fops_llseek/p' | head -220
