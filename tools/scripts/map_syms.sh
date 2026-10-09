#!/bin/bash
cd ~/ghostlock || exit 1
echo "===== configfs (iter/read/write/bin) ====="
grep -E ' [A-Za-z_]*configfs[A-Za-z_.]*$' kernel/kallsyms_fixed.txt | sort -k1
echo
echo "===== splice_read / splice_write ====="
grep -E ' [A-Za-z_]*(splice_read|splice_write)$' kernel/kallsyms_fixed.txt
echo
echo "===== blob_sizes / selinux blob ====="
grep -E ' [A-Za-z_]*(blob_sizes|selinux_blob)[A-Za-z_]*$' kernel/kallsyms_fixed.txt
echo
echo "===== ashmem ====="
grep -E ' [A-Za-z_]*ashmem[A-Za-z_.]*$' kernel/kallsyms_fixed.txt
echo
echo "===== futex_wait_requeue_pi / rt_mutex ====="
grep -E ' (futex_wait_requeue_pi|rt_mutex_adjust_prio_chain|rt_mutex_start_proxy_lock|remove_waiter)$' kernel/kallsyms_fixed.txt
