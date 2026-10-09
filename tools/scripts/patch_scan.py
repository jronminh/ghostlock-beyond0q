p='src/core/fops.c'
s=open(p).read()
a='''    if (env_flag("SSOPT_RANGE", 0)) {'''
b='''    if (env_flag("SSOPT_SCAN", 0)) {
      /* one-run probe: distinct non-canonical value per buf slot so the panic
       * register x24 reveals which slot lands on waiter->lock */
      for (int i = 0; i < 0x60; i += 8)
        put64(buf, i, 0x1a2b00000000ULL + (uint64_t)i);
    } else if (env_flag("SSOPT_RANGE", 0)) {'''
assert s.count(a)==1,('scan anchor',s.count(a)); s=s.replace(a,b,1)
a='''    socklen_t paint_len = env_flag("SSOPT_RANGE", 0) ? 0x60 : 0x50;'''
b='''    socklen_t paint_len = (env_flag("SSOPT_RANGE", 0) || env_flag("SSOPT_SCAN", 0))
                               ? 0x60 : 0x50;'''
assert s.count(a)==1,('len2 anchor',s.count(a)); s=s.replace(a,b,1)
open(p,'w').write(s); print('SSOPT_SCAN added')
