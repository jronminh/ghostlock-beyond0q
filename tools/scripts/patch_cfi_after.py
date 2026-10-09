p = 'src/core/main.c'
s = open(p).read()
a = '''#else
  run_main_route_threads();
#endif
  TIMER("  PI route done");'''
b = '''#else
  run_main_route_threads();
#endif
#ifndef COMPAT32
  /* the 32-bit child did the redirect; the 64-bit parent establishes
   * configfs r/w (and the rest of the chain) from here. */
  if (mode == 4 && active_offsets && active_offsets->off_system_unbound_wq &&
      !root_child_done) {
    try_cfi_stage();
  }
#endif
  TIMER("  PI route done");'''
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('added try_cfi_stage after route child')
