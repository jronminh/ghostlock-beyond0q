#!/usr/bin/env python3
# Same park-until-walked handshake for the SLIDE route so its res_in task/lock
# survive until the consumer drives the PI walk.
p = 'src/core/slide.c'
s = open(p).read()

a = 'static atomic_int slide_consume_last_sched_errno;'
assert s.count(a) == 1
s = s.replace(a, a + '\nstatic atomic_int slide_select_done;\nstatic atomic_int slide_walk_done;', 1)

# reset before select
a = '''  atomic_store(&slide_consume_go, 1);
  errno = 0;'''
b = '''  atomic_store(&slide_consume_go, 1);
  atomic_store(&slide_select_done, 0);
  atomic_store(&slide_walk_done, 0);
  errno = 0;'''
assert s.count(a) == 1
s = s.replace(a, b, 1)

# park after select
a = '''  int saved_errno = errno;
  atomic_store(&slide_consume_go, 0);'''
b = '''  int saved_errno = errno;
  atomic_store(&slide_select_done, 1);
  for (int spin = 0;
       spin < 2000000000 && !atomic_load(&slide_walk_done);
       spin++) {
    __asm__ volatile("yield" ::: "memory");
  }
  atomic_store(&slide_consume_go, 0);'''
assert s.count(a) == 1
s = s.replace(a, b, 1)

# consumer: wait for select_done before sched_setattr, signal walk_done after
a = '''    seen = seq;
    atomic_store(&slide_consume_seen, seen);'''
b = '''    seen = seq;
    atomic_store(&slide_consume_seen, seen);
    for (int spin = 0;
         spin < 2000000000 && !atomic_load(&slide_select_done) &&
         !atomic_load(&slide_consume_stop);
         spin++) {
      __asm__ volatile("yield" ::: "memory");
    }'''
assert s.count(a) == 1
s = s.replace(a, b, 1)

a = '''    atomic_store(&slide_consume_last_sched_ret, (int)ret);
    atomic_store(&slide_consume_last_sched_errno, saved_errno);'''
b = '''    atomic_store(&slide_consume_last_sched_ret, (int)ret);
    atomic_store(&slide_consume_last_sched_errno, saved_errno);
    atomic_store(&slide_walk_done, 1);'''
assert s.count(a) == 1
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('slide.c handshake ok')
