#!/bin/bash
S=/root/ghostlock/src/g9700
echo "==request_module in exec.c=="
grep -n "request_module" "$S/fs/exec.c"
echo "==printable/search_binary_handler=="
awk '/^static int search_binary_handler\(/,/^}/' "$S/fs/exec.c"
echo "==bprm read size=="
grep -n "BINPRM_BUF_SIZE" "$S/include/uapi/linux/binfmts.h"
