p='src/core/slide.c'
s=open(p).read()
a='''int slide_pselect_words_per_set(void) {
  int bits_per_word = (int)(8 * sizeof(unsigned long));
  return (SLIDE_PSELECT_NFDS + bits_per_word - 1) / bits_per_word;
}'''
b='''int slide_pselect_words_per_set(void) {
  /* kernel fd_set_bits always uses native 64-bit longs (BITS_PER_LONG == 64),
   * including the compat path; verified in compat_core_sys_select
   * (size = FDS_LONGS(n)*8, FDS_LONGS = (n+63)/64).  Must be 64-bit words in
   * both builds. */
  return (SLIDE_PSELECT_NFDS + 63) / 64;
}'''
assert s.count(a)==1, s.count(a)
s=s.replace(a,b,1)
open(p,'w').write(s)
print('slide words_per_set patched')
