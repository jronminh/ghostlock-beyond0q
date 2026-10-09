#!/bin/bash
VML="$HOME/ghostlock/kernel/vmlinux.elf"
echo "############ configfs_read_file ############"
aarch64-linux-gnu-objdump -d --start-address=0x38522ac --stop-address=0x38523f0 "$VML"
echo "############ configfs_write_bin_file ############"
aarch64-linux-gnu-objdump -d --start-address=0x38527dc --stop-address=0x3852920 "$VML"
