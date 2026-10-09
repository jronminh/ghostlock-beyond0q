import re
p="/root/ghostlock/ghostlock-oneplus/src/core/pipe_physrw.c"
L=open(p,errors="ignore").read().splitlines()
for i,l in enumerate(L):
    if "cache gate" in l or "pipe_page_slab_cache" in l or "pipe_page_type" in l or "cache_gate" in l:
        print("%4d %s" % (i+1, l.strip()[:150]))
print("=== scan fn head ===")
for i,l in enumerate(L):
    if re.search(r"static .*pr_scan|match_pipe_buffer|prepare_pipe_buffers", l):
        print("%4d %s" % (i+1, l.strip()[:150]))
