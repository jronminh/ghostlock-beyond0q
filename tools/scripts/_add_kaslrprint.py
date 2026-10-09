F="/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s=open(F).read()
assert "kaslr read:" not in s
old="""  if (!is_kernel_ptr(kaslr_open_ptr) || !is_kernel_ptr(kaslr_ioctl_ptr) ||
      !is_kernel_ptr(kaslr_mmap_ptr) || !is_kernel_ptr(kaslr_release_ptr) ||
      !is_kernel_ptr(kaslr_show_fdinfo_ptr)) {
    kaslr_step = 1;
    return 0;
  }
"""
new="""  pr_info("kaslr read: alias=%016llx open=%016llx ioctl=%016llx mmap=%016llx "
          "rel=%016llx fdin=%016llx\\n",
          (unsigned long long)kaslr_fops_alias,
          (unsigned long long)kaslr_open_ptr,
          (unsigned long long)kaslr_ioctl_ptr,
          (unsigned long long)kaslr_mmap_ptr,
          (unsigned long long)kaslr_release_ptr,
          (unsigned long long)kaslr_show_fdinfo_ptr);
  fsync(1);
  if (!is_kernel_ptr(kaslr_open_ptr) || !is_kernel_ptr(kaslr_ioctl_ptr) ||
      !is_kernel_ptr(kaslr_mmap_ptr) || !is_kernel_ptr(kaslr_release_ptr) ||
      !is_kernel_ptr(kaslr_show_fdinfo_ptr)) {
    kaslr_step = 1;
    return 0;
  }
"""
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
open(F,"w").write(s)
print("fops.c: kaslr read print")
