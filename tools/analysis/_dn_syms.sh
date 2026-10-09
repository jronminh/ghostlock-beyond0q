#!/bin/bash
VML="$HOME/ghostlock/kernel/vmlinux.elf"
nm "$VML" > /tmp/dnsyms.txt
echo "=== symbol addresses ==="
grep -E ' (configfs_read_file|configfs_write_bin_file|configfs_read_bin_file|fill_read_buffer|kmem_cache_alloc|kmem_cache_alloc_trace|kmalloc_caches|anon_pipe_buf_ops|__kmalloc|__kmalloc_track_caller|kmem_cache_create|get_partial|__slab_free|allocate_slab|new_slab|__per_cpu_offset|kmem_cache_node|free_partial|unfreeze_partials|deactivate_slab|___slab_alloc)$' /tmp/dnsyms.txt
echo "=== done ==="
