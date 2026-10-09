#!/bin/bash
cd /root/ghostlock/ghostlock-oneplus
echo "===== ORIGINAL util.c: prepare_skb_payload (fake page) ====="
git show HEAD:src/core/util.c | sed -n '/prepare_skb_payload/,/^}/p' | head -120
echo
echo "===== ORIGINAL fops.c: try_cfi_stage ====="
git show HEAD:src/core/fops.c | sed -n '/^int try_cfi_stage/,/^}/p' | head -140
