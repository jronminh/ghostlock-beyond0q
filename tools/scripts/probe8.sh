#!/bin/bash
K=/root/ghostlock/kernel
grep -nE 'compat_SyS_select$|compat_core_sys_select$|core_sys_select$|do_select$|futex_wait_requeue_pi$|futex_lock_pi$|SyS_futex$|compat_SyS_futex$|do_futex$|get_futex_key$' $K/kallsyms_fixed.txt
echo "--- beyond0q table head ---"
sed -n '20,70p' /root/ghostlock/ghostlock-oneplus/src/devices/beyond0q/offsets.h
