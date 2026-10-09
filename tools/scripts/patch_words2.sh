#!/bin/bash
cd /root/ghostlock/ghostlock-oneplus
python3 /mnt/e/Library/Desktop/ghostlock/patch_words2.py
echo "--- fops ---"
grep -n -A2 "pselect_words_per_set" src/core/fops.c | head
echo "--- slide ---"
grep -n -A2 "slide_pselect_words_per_set" src/core/slide.c | head
