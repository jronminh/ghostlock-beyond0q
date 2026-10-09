#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
S=/root/ghostlock/src/g9700
echo "###### SKB_DATA_DELTA: định nghĩa + comment + nơi dùng ######"
grep -rn "SKB_DATA_DELTA" $R/ $R/../.. 2>/dev/null | grep -v Binary | head
grep -rnE "0xe80|0xE80|SKB_DATA" $R/common.h | head
echo
echo "###### SKB_* constants (common.h) ######"
grep -nE 'SKB_|ORDER3|MM_ORDER|SKB_RECLAIM|PAGE_SHIFT' $R/common.h | head -30
echo
echo "###### struct skb_shared_info (4.14) ######"
awk '/^struct skb_shared_info {/,/^};/' $S/include/linux/skbuff.h
echo
echo "###### alloc_skb / __alloc_skb / kmalloc_reserve (data layout) ######"
awk '/^struct sk_buff \*__alloc_skb/,/^}/' $S/net/core/skbuff.c | head -60
