#!/usr/bin/env python3
# Gate the PI-walk trigger (sched_setattr in the consumer) so we can tell whether
# the panic is inside select()/fd-setup or in the rt_mutex chain walk itself.
p = 'src/core/main.c'
s = open(p).read()
a = '        errno = 0;\n        long sched_ret = sched_setattr_tid(tid, PSELECT_CONSUMER_NICE);'
b = ('        errno = 0;\n'
     '        long sched_ret = env_flag("NO_WALK", 0)\n'
     '                             ? 0\n'
     '                             : sched_setattr_tid(tid, PSELECT_CONSUMER_NICE);')
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('patched main.c NO_WALK gate')
