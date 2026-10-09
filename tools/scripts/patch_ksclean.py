p='src/core/kernelsnitch/kernelsnitch.h'
s=open(p).read()

# 1) detach the sleeper threads so they are reaped when they return
a='''    struct kernelsnitch_shared_state *ks = inc_arg->ks;
    size_t id = inc_arg->id;
    SYSCHK(__futex((unsigned int *)&ks->inc_futex[id], FUTEX_WAIT_PRIVATE, 0, NULL, NULL, 0));'''
b='''    struct kernelsnitch_shared_state *ks = inc_arg->ks;
    size_t id = inc_arg->id;
    pthread_detach(pthread_self());
    SYSCHK(__futex((unsigned int *)&ks->inc_futex[id], FUTEX_WAIT_PRIVATE, 0, NULL, NULL, 0));'''
assert s.count(a)==1,('inc anchor',s.count(a)); s=s.replace(a,b,1)

# 2) wake the APPENDED_FUTEXES (id=128) sleepers before munmap so they don't leak
a='''size_t kernelsnitch_cleanup(struct kernelsnitch_shared_state *ks)
{
    ASSERT_pr((ks->state == KERNELSNITCH_MM_FOUND || ks->state == KERNELSNITCH_MM_NOT_FOUND), "wrong state\\n");
    munmap((void *)ks->times, sizeof(size_t)*ks->total_futexes);'''
b='''size_t kernelsnitch_cleanup(struct kernelsnitch_shared_state *ks)
{
    ASSERT_pr((ks->state == KERNELSNITCH_MM_FOUND || ks->state == KERNELSNITCH_MM_NOT_FOUND), "wrong state\\n");
    /* __increase() parked APPENDED_FUTEXES detached threads in
     * FUTEX_WAIT_PRIVATE on &inc_futex[128]; wake them so they exit instead of
     * leaking blocked forever after we unmap ks (they hold kernel stacks and
     * pollute the process thread list into the exploit route). */
    __futex((unsigned int *)&ks->inc_futex[128], FUTEX_WAKE_PRIVATE,
            (unsigned int)-1, NULL, NULL, 0);
    for (int _i = 0; _i < 200; ++_i) sched_yield();
    munmap((void *)ks->times, sizeof(size_t)*ks->total_futexes);'''
assert s.count(a)==1,('cleanup anchor',s.count(a)); s=s.replace(a,b,1)

open(p,'w').write(s)
print('kernelsnitch cleanup: wake+detach sleepers')
