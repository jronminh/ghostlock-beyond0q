F="/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s=open(F).read()
assert "SHOW_FDINFO gate" not in s
old1="""  if (!is_kernel_ptr(kaslr_open_ptr) || !is_kernel_ptr(kaslr_ioctl_ptr) ||
      !is_kernel_ptr(kaslr_mmap_ptr) || !is_kernel_ptr(kaslr_release_ptr) ||
      !is_kernel_ptr(kaslr_show_fdinfo_ptr)) {
"""
new1="""  /* SHOW_FDINFO gate: this kernel's ashmem_fops has show_fdinfo == 0 */
  if (!is_kernel_ptr(kaslr_open_ptr) || !is_kernel_ptr(kaslr_ioctl_ptr) ||
      !is_kernel_ptr(kaslr_mmap_ptr) || !is_kernel_ptr(kaslr_release_ptr)) {
"""
assert s.count(old1)==1, s.count(old1)
s=s.replace(old1,new1,1)
old2="""  if (kaslr_ioctl_ptr != kaslr_expected_ioctl ||
      kaslr_mmap_ptr != kaslr_expected_mmap ||
      kaslr_release_ptr != kaslr_expected_release ||
      kaslr_show_fdinfo_ptr != kaslr_expected_show_fdinfo) {
"""
new2="""  if (kaslr_ioctl_ptr != kaslr_expected_ioctl ||
      kaslr_mmap_ptr != kaslr_expected_mmap ||
      kaslr_release_ptr != kaslr_expected_release) {
"""
assert s.count(old2)==1, s.count(old2)
s=s.replace(old2,new2,1)
open(F,"w").write(s)
print("fops.c: show_fdinfo gate removed")
