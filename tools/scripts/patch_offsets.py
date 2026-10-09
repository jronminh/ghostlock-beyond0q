import re

# ---- 1) device table struct: add per-kernel waiter pi_tree + task usage ----
p='src/devices/offsets.h'
s=open(p).read()
a='  uint32_t mm_owner;\n  uint32_t waiter_compact;\n  uint64_t kimage_text_base;'
b=('  uint32_t mm_owner;\n  uint32_t waiter_compact;\n'
   '  /* rt_mutex_waiter layout details (0 = target.h default, 6.x nested) */\n'
   '  uint32_t waiter_pi_tree_off;  /* offsetof(rt_mutex_waiter, pi_tree_entry) */\n'
   '  uint32_t task_usage_off;      /* offsetof(task_struct, usage) */\n'
   '  uint64_t kimage_text_base;')
assert s.count(a)==1,('offsets struct',s.count(a)); s=s.replace(a,b,1)
open(p,'w').write(s); print('offsets.h: fields added')

# ---- 2) beyond0q: fix ashmem fops field (+0x10) and add 4.14 waiter/usage ----
p='src/devices/beyond0q/offsets.h'
s=open(p).read()
a='  .off_ashmem_misc_fops = 0x02BB1750ULL,'
b=('  /* miscdevice.fops field = &ashmem_misc + 0x10 (kallsyms ashmem_misc=0x2bb1750\n'
   '   * is the STRUCT base; the .fops pointer is at +0x10). */\n'
   '  .off_ashmem_misc_fops = 0x02BB1760ULL,')
assert s.count(a)==1,('beyond0q misc',s.count(a)); s=s.replace(a,b,1)
a='  .mm_owner = 0x328, .waiter_compact = 1,'
b='  .mm_owner = 0x328, .waiter_compact = 1, .waiter_pi_tree_off = 0x18, .task_usage_off = 0x68,'
assert s.count(a)==1,('beyond0q compact',s.count(a)); s=s.replace(a,b,1)
open(p,'w').write(s); print('beyond0q: misc fops + waiter/usage fixed')

# ---- 3) runtime_struct_offsets.h: make them per-device ----
p='src/core/runtime_struct_offsets.h'
s=open(p).read()
assert '#undef FAKE_TASK_PI_BLOCKED_ON_OFF' in s
s=s.replace('#undef FAKE_TASK_PI_BLOCKED_ON_OFF',
            '#undef FAKE_TASK_PI_BLOCKED_ON_OFF\n#undef FAKE_TASK_USAGE_OFF\n#undef FAKE_WAITER_PI_TREE_ENTRY_OFF',1)
a='#define FAKE_TASK_PI_BLOCKED_ON_OFF  _RSO(task_pi_blocked_on, 0xA18)'
assert s.count(a)==1,('rso blocked',s.count(a))
s=s.replace(a,
  a+'\n'
  '#define FAKE_TASK_USAGE_OFF          _RSO(task_usage_off, 0x40)\n'
  '#define FAKE_WAITER_PI_TREE_ENTRY_OFF _RSO(waiter_pi_tree_off, 0x28)',1)
open(p,'w').write(s); print('runtime_struct_offsets.h: RSO wiring added')
