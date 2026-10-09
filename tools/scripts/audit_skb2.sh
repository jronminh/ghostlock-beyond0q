#!/bin/bash
S=/root/ghostlock/src/g9700
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### unix_stream_sendmsg -> sock_alloc_send_pskb -> alloc_skb (headroom) ######"
sed -n '/static int unix_stream_sendmsg/,/^}/p' $S/net/unix/af_unix.c | head -90
echo
echo "###### sock_alloc_send_pskb ######"
sed -n '/struct sk_buff \*sock_alloc_send_pskb/,/^}/p' $S/net/core/sock.c | head -70
echo
echo "###### exploit: đoạn sendmsg reclaim + shaping (util.c ~770-840) ######"
sed -n '770,845p' $R/util.c
