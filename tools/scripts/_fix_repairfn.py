import os, re
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
# extract the misplaced block
m=re.search(r"/\* Rewrite the fake fops table.*?\n\}\n\n", s, re.S)
assert m, "block not found"
block=m.group(0)
s=s[:m.start()]+s[m.end():]
# insert after perf_page_map definition
anchor="static unsigned char *perf_page_map;"
assert s.count(anchor)>=1, ("perf_page_map anchor", s.count(anchor))
s=s.replace(anchor, anchor+"\n\n"+block.rstrip()+"\n", 1)
open(U,"w").write(s)
print("util.c: moved repair fn after perf_page_map")
