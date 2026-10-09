p = 'src/core/fops.c'
s = open(p).read()
a = '''    int ret = setsockopt(sock_paint_fd, SOL_SOCKET, 1000, buf,
                         (socklen_t)sizeof buf);
    int saved_errno = errno;
    atomic_store(&pselect_select_done, 1);'''
b = '''    int ret = setsockopt(sock_paint_fd, SOL_SOCKET, 1000, buf,
                         (socklen_t)sizeof buf);
    int saved_errno = errno;
    pr_info("ssopt paintret ret=%d errno=%d fd=%d base=%016zx task=%016zx "
            "lock=%016zx\\n",
            ret, saved_errno, sock_paint_fd, page_base, fake_task, fake_lock);
    atomic_store(&pselect_select_done, 1);'''
assert s.count(a) == 1, ('anchor', s.count(a))
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('diagnostic log added')
