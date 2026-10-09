p='src/core/kernelsnitch/kernelsnitch.h'
s=open(p).read()
a='''    __futex((unsigned int *)&ks->inc_futex[128], FUTEX_WAKE_PRIVATE,
            (unsigned int)-1, NULL, NULL, 0);
    for (int _i = 0; _i < 200; ++_i) sched_yield();'''
b='''    for (int _i = 0; _i < 5000; ++_i) {
      __futex((unsigned int *)&ks->inc_futex[128], FUTEX_WAKE_PRIVATE,
              (unsigned int)-1, NULL, NULL, 0);
      sched_yield();
    }'''
assert s.count(a)==1,('wake anchor',s.count(a)); s=s.replace(a,b,1)
open(p,'w').write(s)
print('robust wake loop')
