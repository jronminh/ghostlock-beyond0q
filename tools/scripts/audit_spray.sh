#!/bin/bash
R=/root/ghostlock/ghostlock-oneplus/src/core
echo "###### spray: socketpair/sendmsg/F_SETPIPE_SZ/CLOEXEC/close ######"
grep -nE 'socketpair|sendmsg|recvmsg|F_SETPIPE_SZ|FD_CLOEXEC|O_CLOEXEC|memfd|close\(|SOCK_|MSG_' $R/util.c | head -50
echo
echo "###### prepare_good_kernel_page + prepare_kernel_page (util.c) ######"
sed -n '/prepare_kernel_page/,/^}/p' $R/util.c | head -90
