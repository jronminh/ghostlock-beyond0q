#!/bin/bash
S=/root/ghostlock/src/g9700
echo "== config: user-helper / module / lsm =="
grep -E 'CONFIG_(UEVENT_HELPER|FW_LOADER|MODPROBE|STATIC_USERMODEHELPER|MODULES|DEFAULT_MMAP_MIN_ADDR|SECURITY_DEFEX|SECURITY_RKP|KNOX|SEC_|RKP|HARDENED_USERCOPY|STRICT_KERNEL_RWX|MODULE_SIG)' "$S/out/.config"
echo
echo "== boot exec hooks (init/main.c, initramfs) =="
grep -rn "INIT_PATH\|ramdisk_execute_command\|call_usermodehelper\|run_init_process" "$S/init/main.c" 2>/dev/null | head -20
echo
echo "== paths on writable partitions referenced by kernel =="
grep -rn '"/data\|/data/\|"/cache\|"/persist\|"/efs\|/sbin/' "$S/kernel" "$S/init" 2>/dev/null | grep -viE '\.o:|\.cmd:|Documentation' | head -30
echo
echo "== modprobe default path =="
grep -rn "CONFIG_MODPROBE_PATH\|modprobe_path\[\]\|/sbin/modprobe" "$S/kernel/kmod.c" "$S/include/linux/kmod.h" 2>/dev/null | head
echo
echo "== Samsung security files present =="
ls "$S/security" 2>/dev/null
find "$S" -maxdepth 3 -type d \( -iname '*defex*' -o -iname '*rkp*' -o -iname '*knox*' -o -iname '*dm-verity*' -o -iname '*sec_*' \) 2>/dev/null | head
