import re
P="/root/ghostlock/ghostlock-oneplus/src/core/pipe_physrw.c"
s=open(P).read()
old="""static uintptr_t pr_kmalloc_caches(void) {
  uint64_t off = (active_offsets && active_offsets->off_kmalloc_caches)
    ? active_offsets->off_kmalloc_caches : KMALLOC_CACHES_OFF;
  return data_addr(KIMAGE_TEXT_BASE + off);
}"""
new="""static uintptr_t pr_kmalloc_caches(void) {
  uint64_t off = (active_offsets && active_offsets->off_kmalloc_caches)
    ? active_offsets->off_kmalloc_caches : KMALLOC_CACHES_OFF;
  /* Known slide -> canonical image mapping (data_addr's linear alias needs an
   * unknown phys delta; see BAN_GIAO 22.2).  kmalloc_caches is read-only. */
  return (kaslr_slide != 0) ? text_addr(KIMAGE_TEXT_BASE + off)
                            : data_addr(KIMAGE_TEXT_BASE + off);
}"""
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
open(P,"w").write(s)
print("pipe_physrw.c: pr_kmalloc_caches canonical")
import glob,os
for fn in ["pipe_physrw.c","root.c","umh_root.c","util.c"]:
    p="/root/ghostlock/ghostlock-oneplus/src/core/"+fn
    for i,l in enumerate(open(p,errors="ignore").read().splitlines(),1):
        if "data_addr" in l and "data_addr(" in l:
            print("%s:%d: %s" % (fn,i,l.strip()[:120]))
