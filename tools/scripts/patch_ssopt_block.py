p = 'src/core/fops.c'
s = open(p).read()

# 1) guarantee a positive consumer delay so the walk fires while T is blocked
a = '''    int delay_usec = route_delay_usec(attempt);
    atomic_store(&main_route_delay_usec, delay_usec);

    pr_info("ssopt pre paint'''
b = '''    int delay_usec = route_delay_usec(attempt);
    if (delay_usec < 20000) delay_usec = 20000;
    atomic_store(&main_route_delay_usec, delay_usec);

    pr_info("ssopt pre paint'''
assert s.count(a) == 1, ('delay anchor', s.count(a))
s = s.replace(a, b, 1)

# 2) block inside a syscall (like the original select()) instead of a userspace spin
a = '''    atomic_store(&pselect_select_done, 1);
    /* The stack copy is done; let it settle, then release the consumer. */
    usleep(20000);
    atomic_store(&punch_consume_go, attempt);
    /* Park in userspace: no further syscall may touch this thread's kernel
     * stack, so the fake waiter stays put for the consumer's walk. */
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }'''
b = '''    atomic_store(&pselect_select_done, 1);
    atomic_store(&punch_consume_go, attempt);
    /* Original design relies on this thread sitting INSIDE a syscall while the
     * consumer fires (the walk reads the dangling waiter off this stack).  Do
     * NOT return to userspace: block in nanosleep, whose tiny frame never
     * reaches the waiter at SP0-0x1b0, so the paint stays intact. */
    for (int nap = 0; nap < 60 && !atomic_load(&pselect_walk_done); nap++) {
      struct timespec sl = {.tv_sec = 0, .tv_nsec = 20000000};
      nanosleep(&sl, NULL);
    }'''
assert s.count(a) == 1, ('block anchor', s.count(a))
s = s.replace(a, b, 1)

open(p, 'w').write(s)
print('nanosleep-block patched')
