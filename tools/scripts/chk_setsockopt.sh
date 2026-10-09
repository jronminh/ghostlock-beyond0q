#!/bin/bash
K=/root/ghostlock/kernel
cd /mnt/e/Library/Desktop/ghostlock
echo "===== analyze_one.py setsockopt ====="
python3 analyze_one.py setsockopt 2>&1 | head -40
echo
echo "===== symbols ====="
grep -nE 'SyS_setsockopt$|compat_SyS_setsockopt$|sock_setsockopt$|__sys_setsockopt$|do_notify_resume$|el0_svc$|do_syscall_64$' $K/kallsyms_fixed.txt
