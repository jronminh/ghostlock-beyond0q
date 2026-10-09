p = 'src/core/fops.c'
s = open(p).read()
old = '''static int route_delay_usec(int attempt) {
  int default_delay = pselect_custom_write_enabled() ? 0 : -1;'''
new = '''static int route_delay_usec(int attempt) {
#ifdef COMPAT32
  /* shift=6 route: select blocks; fire the walk while do_select() is parked. */
  int default_delay = 20000;
#else
  int default_delay = pselect_custom_write_enabled() ? 0 : -1;
#endif'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w').write(s)
print('patched route_delay_usec for COMPAT32')
