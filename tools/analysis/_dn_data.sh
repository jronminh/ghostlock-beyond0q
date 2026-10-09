#!/bin/bash
VML="$HOME/ghostlock/kernel/vmlinux.elf"
echo "=== anon_pipe_buf_ops @0x4d354e8 (4 ptrs) ==="
aarch64-linux-gnu-objdump -s --start-address=0x4d354e8 --stop-address=0x4d35528 "$VML" | tail -n +5
echo "=== kmalloc_caches @0x578b790 (56 ptrs = 0x1c0) ==="
aarch64-linux-gnu-objdump -s --start-address=0x578b790 --stop-address=0x578b950 "$VML" | tail -n +5
echo "=== kmem_cache_node @0x62d0120 ==="
aarch64-linux-gnu-objdump -s --start-address=0x62d0120 --stop-address=0x62d0160 "$VML" | tail -n +5
