#!/usr/bin/env python3
# Deterministic res_in window: for shift=12 the fake waiter's task/lock live in
# res_in, which do_select fills only when it returns.  So the waiter thread must
# be parked (in userspace, no syscall that could clobber its kernel stack) while
# the consumer thread drives rt_mutex_adjust_pi() on it.
p = 'src/core/common.h'
s = open(p).read()
a = 'extern atomic_int main_route_delay_usec;'
assert s.count(a) == 1
s = s.replace(a, a + '\nextern atomic_int pselect_select_done;\nextern atomic_int pselect_walk_done;', 1)
open(p, 'w').write(s)
print('common.h ok')

p = 'src/core/main.c'
s = open(p).read()
a = 'atomic_int main_route_delay_usec;'
assert s.count(a) == 1
s = s.replace(a, a + '\natomic_int pselect_select_done;\natomic_int pselect_walk_done;', 1)

a = '''  atomic_store(&punch_consume_go, 0); atomic_store(&punch_consume_stop, 0);
  atomic_store(&consumer_calls, 0); atomic_store(&consumer_success, 0);
  atomic_store(&main_route_delay_usec, PSELECT_ENTER_DELAY_USEC);'''
b = '''  atomic_store(&punch_consume_go, 0); atomic_store(&punch_consume_stop, 0);
  atomic_store(&consumer_calls, 0); atomic_store(&consumer_success, 0);
  atomic_store(&pselect_select_done, 0); atomic_store(&pselect_walk_done, 0);
  atomic_store(&main_route_delay_usec, PSELECT_ENTER_DELAY_USEC);'''
assert s.count(a) == 1
s = s.replace(a, b, 1)

a = '''    seen = seq;
    int tid = atomic_load(&waiter_tid);
    int calls_this_seq = 0;'''
b = '''    seen = seq;
    int tid = atomic_load(&waiter_tid);
    int calls_this_seq = 0;
    /* Park until the waiter thread has finished select() and res_in holds the
     * fake rt_mutex_waiter (task/lock). */
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_select_done) &&
         !atomic_load(&punch_consume_stop);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }'''
assert s.count(a) == 1
s = s.replace(a, b, 1)

a = '''        if (sched_ret == 0) atomic_fetch_add(&consumer_success, 1);
        calls_this_seq++;'''
b = '''        if (sched_ret == 0) atomic_fetch_add(&consumer_success, 1);
        atomic_store(&pselect_walk_done, 1);
        calls_this_seq++;'''
assert s.count(a) == 1
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('main.c ok')

p = 'src/core/fops.c'
s = open(p).read()
# reset flags BEFORE the trigger so a stale value can't be observed
a = '''    atomic_store(&punch_consume_stop, 0);
    int delay_usec = route_delay_usec(route_attempt);'''
b = '''    atomic_store(&punch_consume_stop, 0);
    atomic_store(&pselect_select_done, 0);
    atomic_store(&pselect_walk_done, 0);
    int delay_usec = route_delay_usec(route_attempt);'''
assert s.count(a) == 1
s = s.replace(a, b, 1)

a = '''    pr_info("pselect pre-select +%.0fms\\n", fops_elapsed_ms(&route_t0));
    errno = 0;
    int ret = select(PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);
    int saved_errno = errno;
    pr_info("pselect post-select +%.0fms ret=%d\\n", fops_elapsed_ms(&route_t0), ret);
    atomic_store(&punch_consume_go, 0);'''
b = '''    pr_info("pselect pre-select +%.0fms\\n", fops_elapsed_ms(&route_t0));
    errno = 0;
    int ret = select(PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);
    int saved_errno = errno;
    /* do_select() filled res_in; park in userspace (no syscall) so the
     * consumer's rt_mutex_adjust_pi() reads the intact fake waiter. */
    atomic_store(&pselect_select_done, 1);
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&pselect_walk_done);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }
    pr_info("pselect post-select +%.0fms ret=%d walked=%d\\n",
            fops_elapsed_ms(&route_t0), ret, atomic_load(&pselect_walk_done));
    atomic_store(&punch_consume_go, 0);'''
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('fops.c ok')
