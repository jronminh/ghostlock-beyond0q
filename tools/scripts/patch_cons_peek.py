#!/usr/bin/env python3
"""patch_cons_peek.py

Quan sát từ CONSUMER: in trạng thái trang giả NGAY sau khi sched_setattr(T) trả
về + fsync.  Lý do: nếu walk hard-lock (spinlock + IRQ off) thì watchdog reset máy
và mọi log *sau* đó (peek của route, sau spin) bị mất.  Consumer ở thread khác,
nên in ở đây sẽ sống sót và cho biết walk đã ghi gì.
Bật bằng SSOPT_PEEK=1.
"""
M = "/root/ghostlock/ghostlock-oneplus/src/core/main.c"
s = open(M).read()

old = """        if (sched_ret == 0) atomic_fetch_add(&consumer_success, 1);
        atomic_store(&pselect_walk_done, 1);"""
new = """        if (sched_ret == 0) atomic_fetch_add(&consumer_success, 1);
        if (env_flag("SSOPT_PEEK", 0)) {
          /* Observe the fake page right after the walk, from THIS thread: if the
           * walk hard-locked (spinlock held, IRQs off) the machine is reset by
           * the watchdog and any later print (route-side peek after its spin)
           * is lost.  page[0x108] (fake_fops->llseek) becomes dbg_rb_right only
           * if chain[7] rb_erase_cached() really ran with our painted node. */
          pr_info("cons peek ret=%ld cl=%d succ=%d "
                  "page[0x00]=%016zx [0x08]=%016zx [0x10]=%016zx "
                  "[0x108]=%016zx [0x110]=%016zx [0x310]=%016zx\\n",
                  sched_ret, atomic_load(&consumer_calls),
                  atomic_load(&consumer_success),
                  (uintptr_t)ssopt_page_readback(0x00),
                  (uintptr_t)ssopt_page_readback(0x08),
                  (uintptr_t)ssopt_page_readback(0x10),
                  (uintptr_t)ssopt_page_readback(0x108),
                  (uintptr_t)ssopt_page_readback(0x110),
                  (uintptr_t)ssopt_page_readback(0x310));
          fsync(1);
        }
        atomic_store(&pselect_walk_done, 1);"""
assert s.count(old) == 1, ("cons peek", s.count(old))
s = s.replace(old, new, 1)
open(M, "w").write(s)
print("main.c: consumer-side page peek (survives a hard lockup)")
