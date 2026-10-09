#!/bin/bash
cd ~/ghostlock || exit 1
echo "===== futex / rtmutex / select symbols ====="
grep -E '\b(futex_wait_requeue_pi|futex_wait|futex_requeue|do_futex|rt_mutex_start_proxy_lock|rt_mutex_adjust_prio_chain|remove_waiter|core_sys_select|do_select|__poll|do_epoll_wait)$' kernel/kallsyms.txt
echo
echo "===== core_sys_select : prologue + sp usage (first 60 insns) ====="
ADDR=$(grep -E ' core_sys_select$' kernel/kallsyms.txt | awk '{print $1}')
echo "core_sys_select @ 0x$ADDR"
aarch64-linux-gnu-objdump -d --start-address=0x$ADDR --stop-address=$((0x$ADDR + 0x180)) kernel/vmlinux.elf 2>/dev/null | sed -n '1,70p'
