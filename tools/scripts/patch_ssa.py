p = 'src/core/util.c'
s = open(p).read()
old = '  long ret = syscall(274, tid, &attr, 0);'
new = '''#ifdef COMPAT32
  long ret = syscall(380 /* __NR_sched_setattr (ARM EABI) */, tid, &attr, 0);
#else
  long ret = syscall(274, tid, &attr, 0);
#endif'''
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)
open(p, 'w').write(s)
print('patched util.c sched_setattr syscall number for COMPAT32')
