import re
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
assert "DIAG writeval" not in s
anchor='  pr_info("  wp=%016llx wr=%016llx wl=%016llx fake_fops=%016llx fake_w0=%016llx base?=%016llx",'
assert s.count(anchor)==1
add='''  pr_info("DIAG writeval pg3c0=%016llx pg318=%016llx pg320=%016llx pg328=%016llx",
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x3c0),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x318),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x320),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x328));
'''
s=s.replace(anchor, add+anchor, 1)
open(U,"w").write(s)
print("util.c: DIAG writeval added")
