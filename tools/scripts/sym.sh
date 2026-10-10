#!/bin/bash
K=/root/ghostlock/kernel/kallsyms_fixed.txt
for s in sig_enforce module_sig_check modules_disabled \
         __arm64_sys_finit_module __arm64_sys_init_module \
         load_module do_init_module commit_creds prepare_kernel_cred \
         init_cred init_task sys_call_table call_usermodehelper_exec_work \
         set_memory_rw set_memory_ro kallsyms_lookup_name \
         selinux_enforcing core_pattern modprobe_path ; do
  printf '%-36s ' "$s"
  grep -w "$s" "$K" | head -1
  echo
done
