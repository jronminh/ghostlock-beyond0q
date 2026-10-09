import re
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
assert "fops page dump" not in s
anchor="  uint64_t owner_before = *(volatile uint64_t *)(p + FOPS_OWNER_OFF);"
assert s.count(anchor)==1
dump = anchor + """
  pr_info("ssopt fops page dump pg[0x100..0x13f] / pg[0x300..0x33f]:");
  for (int q = 0; q < 0x40; q += 8) {
    pr_info("  pg[%03x]=%016llx  pg[%03x]=%016llx",
            0x100+q, (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x100+q),
            0x300+q, (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x300+q));
  }
  pr_info("  wp=%016llx wr=%016llx wl=%016llx fake_fops=%016llx fake_w0=%016llx base?=%016llx",
          (unsigned long long)ssopt_write_pc, (unsigned long long)ssopt_write_right,
          (unsigned long long)ssopt_write_left, (unsigned long long)fake_fops,
          (unsigned long long)fake_w0, (unsigned long long)(fake_fops - (FOPS_TABLE_OFF-LOCK_OFF)));
  fsync(1);"""
s=s.replace(anchor, dump, 1)
open(U,"w").write(s)
print("util.c: added page dump")
