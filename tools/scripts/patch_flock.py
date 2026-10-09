p='src/core/main.c'
s=open(p).read()
a='''  fake_lock = base + (int64_t)(LOCK_OFF + SKB_DATA_DELTA);'''
b='''  fake_lock = base + (int64_t)(LOCK_OFF + SKB_DATA_DELTA);
  { /* diagnostic: force an arbitrary (e.g. unmapped) lock value */
    const char *fo = getenv("FAKE_LOCK_OVERRIDE");
    if (fo && *fo) fake_lock = strtoull(fo, NULL, 16);
  }'''
assert s.count(a)==1,('anchor',s.count(a))
s=s.replace(a,b,1)
open(p,'w').write(s)
print('FAKE_LOCK_OVERRIDE added')
