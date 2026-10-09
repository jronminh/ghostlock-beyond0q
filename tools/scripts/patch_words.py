p='src/core/fops.c'
s=open(p).read()
a='''static int pselect_words_per_set(void) {
  int bits_per_word = (int)(8 * sizeof(unsigned long));
  return (PSELECT_ROUTE_NFDS + bits_per_word - 1) / bits_per_word;
}'''
b='''static int pselect_words_per_set(void) {
  /* The kernel's struct fd_set_bits always uses native 64-bit longs
   * (BITS_PER_LONG == 64) even on the compat (32-bit) path -- verified in
   * compat_core_sys_select: size = FDS_LONGS(n)*8 with FDS_LONGS = (n+63)/64.
   * So the per-set word count must be computed with 64-bit words in both the
   * 64-bit and 32-bit builds.  sizeof(unsigned long) is 4 in the armhf child,
   * which previously yielded 10 instead of 5 and misplaced every painted
   * waiter field by 5 longs (40 bytes). */
  return (PSELECT_ROUTE_NFDS + 63) / 64;
}'''
assert s.count(a)==1, s.count(a)
s=s.replace(a,b,1)
open(p,'w').write(s)
print('words_per_set patched')
