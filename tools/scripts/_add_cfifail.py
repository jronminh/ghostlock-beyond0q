F="/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s=open(F).read()
assert "cfi FAIL step" not in s
old="""fail:
  if (dirty) {
"""
new="""fail:
  pr_info("cfi FAIL step=%d errno=%d (kaslr_step=%d)\\n", cfi_last_step,
          cfi_last_errno, kaslr_step);
  fsync(1);
  if (dirty) {
"""
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
open(F,"w").write(s)
print("fops.c: cfi FAIL print")
