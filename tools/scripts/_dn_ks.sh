#!/bin/bash
cd "$HOME/ghostlock/kernel"
for f in kallsyms.txt kallsyms2.txt kallsyms_fixed.txt; do
  echo "=== $f (head) ==="
  head -3 "$f"
  echo "--- matches ---"
  grep -E ' (configfs_read_file|configfs_write_bin_file|anon_pipe_buf_ops|kmalloc_caches|__per_cpu_offset|kmem_cache_node)$' "$f"
done
