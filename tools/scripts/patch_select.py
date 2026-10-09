#!/usr/bin/env python3
# Force the pselect route to use the *select* syscall (__NR_select=1067),
# not glibc's select() which issues pselect6 (__NR_pselect6=72).
#
# Why: the freed rt_mutex_waiter (from do_futex) sits at stack_fds+0x40
# relative to the select-syscall frame (sys_select, frame 0x80), i.e. word 8.
# glibc select() -> pselect6 (sys_pselect6, frame 0xa0) shifts stack_fds down
# by 0x20, making the waiter word 12 -> task/lock land in the kernel-written
# res_* buffers instead of the user-controlled in/out/ex bitmaps.
import re, sys

p = 'src/core/fops.c'
s = open(p).read()
orig = s

if '__NR_select' not in s:
    anchor = '#include <time.h>'
    assert anchor in s, 'time.h include not found'
    s = s.replace(anchor,
                  anchor + '\n#ifndef __NR_select\n#define __NR_select 1067\n#endif',
                  1)

old = 'int ret = select(PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);'
new = ('/* sys_select (nr 1067), NOT glibc select() (=pselect6, frame 0xa0).\n'
       '     * sys_select frame is 0x80 -> waiter lands at stack_fds word 8,\n'
       '     * matching the shift=8 placement below. */\n'
       '    int ret = syscall(__NR_select, PSELECT_ROUTE_NFDS, &in, &out, &ex, &timeout);')
assert old in s, 'select() call site not found'
s = s.replace(old, new, 1)

if s == orig:
    print('no change')
else:
    open(p, 'w').write(s)
    print('patched fops.c: select() -> syscall(__NR_select)')
