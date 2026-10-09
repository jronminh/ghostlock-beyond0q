#!/usr/bin/env python3
# Diagnostic: gate mode-4's write target with WRITE4_SCRATCH so we can tell
# whether the panic comes from writing fake_fops to a WRONG phys alias
# (kernel_phys_load) or from the fake-tree topology itself.
p = 'src/core/util.c'
s = open(p).read()
a = '''    write_pc = fake_fops;
    write_right = data_addr(ASHMEM_MISC_FOPS);
    write_left = 0;'''
b = '''    write_pc = fake_fops;
    write_right = data_addr(ASHMEM_MISC_FOPS);
    if (env_flag("WRITE4_SCRATCH", 0))
      write_right = payload_base + SCRATCH_OFF + 0x40; /* harmless: our page */
    write_left = 0;'''
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('patched util.c mode-4 write target gate')
