import re
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
assert "WRITE_PC_TEST" not in s
old = """    write_pc = fake_fops;
    write_right = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                     : data_addr(ASHMEM_MISC_FOPS);
"""
new = """    { /* diagnostic: allow overriding the value written by mode-4 */
      const char *wpt = getenv("WRITE_PC_TEST");
      write_pc = (wpt && *wpt) ? strtoull(wpt, NULL, 0) : fake_fops;
    }
    write_right = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                     : data_addr(ASHMEM_MISC_FOPS);
"""
assert s.count(old)==1, ("mode4 write_pc", s.count(old))
s=s.replace(old,new,1)
open(U,"w").write(s)
print("util.c: WRITE_PC_TEST added")
