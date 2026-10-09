import re
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
T="/root/ghostlock/ghostlock-oneplus/src/core/target.h"
s=open(U).read()
assert "fops slots:" not in s
anchor='  pr_info("  wp=%016llx wr=%016llx wl=%016llx fake_fops=%016llx fake_w0=%016llx base?=%016llx",'
add='''  pr_info("  fops slots: owner=%016llx llseek=%016llx read_iter=%016llx "
          "write_iter=%016llx ioctl=%016llx open=%016llx release=%016llx\\n",
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_OWNER_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_LLSEEK_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_READ_ITER_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_WRITE_ITER_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_IOCTL_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_OPEN_OFF),
          (unsigned long long)*(volatile uint64_t *)(p+FOPS_RELEASE_OFF));
'''
assert s.count(anchor)==1
s=s.replace(anchor, add+anchor, 1)
open(U,"w").write(s)
print("util.c: fops slots print")

t=open(T).read()
import re as _re
for name,val in [("CFG_PAGE_OFF","16"),("CFG_NEEDS_READ_FILL_OFF","0x48"),
                 ("CFG_BIN_BUFFER_OFF","0x50"),("CFG_BIN_BUFFER_SIZE_OFF","0x58"),
                 ("CFG_CB_MAX_SIZE_OFF","0x5c")]:
    t2=_re.sub(r"(#define %s)\s+[0-9xA-Fa-f]+" % name, r"\1            %s" % val, t)
    assert t2!=t or ("#define %s"%name) in t, name
    t=t2
open(T,"w").write(t)
print("target.h: CFG_* updated")
# show
for l in open(T).read().splitlines():
    if "CFG_" in l and "define" in l: print("   "+l.strip())
