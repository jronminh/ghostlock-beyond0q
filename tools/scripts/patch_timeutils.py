#!/usr/bin/env python3
# AArch32 needs CP15 MRRC for the architected counter; mrs cntvct_el0 is AArch64.
p = 'src/core/kernelsnitch/timeutils.h'
s = open(p).read()
old = '''#elif defined(__ARM)
    unsigned long long vct;
    asm volatile("isb" ::: "memory");
    asm volatile("mrs %0, cntvct_el0" : "=r"(vct));
    asm volatile("isb" ::: "memory");
    return (size_t)vct;'''
new = '''#elif defined(__ARM)
    unsigned long long vct;
    asm volatile("isb" ::: "memory");
#if defined(__aarch64__)
    asm volatile("mrs %0, cntvct_el0" : "=r"(vct));
#else
    { unsigned int __lo, __hi;
      asm volatile("mrrc p15, 1, %0, %1, c14" : "=r"(__lo), "=r"(__hi));
      vct = ((unsigned long long)__hi << 32) | __lo; }
#endif
    asm volatile("isb" ::: "memory");
    return (size_t)vct;'''
assert s.count(old) == 2, s.count(old)
s = s.replace(old, new)
open(p, 'w').write(s)
print('patched timeutils.h (rdtsc AArch32)')
