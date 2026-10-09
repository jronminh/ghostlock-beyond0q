p = 'src/core/fops.c'
s = open(p).read()

# Move punch_consume_go to AFTER the paint (plus a small settle delay) so the
# consumer cannot fire while sock_setsockopt is still copying the buffer.
a = '''    int delay_usec = route_delay_usec(attempt);
    atomic_store(&main_route_delay_usec, delay_usec);
    atomic_store(&punch_consume_go, attempt);

    pr_info("ssopt pre paint'''
b = '''    int delay_usec = route_delay_usec(attempt);
    atomic_store(&main_route_delay_usec, delay_usec);

    pr_info("ssopt pre paint'''
assert s.count(a) == 1, ('A', s.count(a))
s = s.replace(a, b, 1)

a = '''    int saved_errno = errno;
    atomic_store(&pselect_select_done, 1);
    /* Park in userspace'''
b = '''    int saved_errno = errno;
    atomic_store(&pselect_select_done, 1);
    /* The stack copy is done; let it settle, then release the consumer. */
    usleep(20000);
    atomic_store(&punch_consume_go, attempt);
    /* Park in userspace'''
assert s.count(a) == 1, ('B', s.count(a))
s = s.replace(a, b, 1)

open(p, 'w').write(s)
print('order patched')
