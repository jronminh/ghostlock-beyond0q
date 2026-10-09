U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
old="""uintptr_t data_addr(uintptr_t image_addr) {
  return p0_data_alias(image_addr);
}"""
new="""uintptr_t data_addr(uintptr_t image_addr) {
  /* Known slide -> canonical image mapping (RW for .data), the same page as the
   * linear alias but independent of the unknown loader phys delta.  See §22.2. */
  if (kaslr_slide != 0) {
    return kaslr_base + (image_addr - KIMAGE_TEXT_BASE);
  }
  return p0_data_alias(image_addr);
}"""
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
open(U,"w").write(s)
print("util.c: data_addr -> canonical when slid")
