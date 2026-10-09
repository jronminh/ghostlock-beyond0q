p = 'src/core/main.c'
s = open(p).read()
a = '  timer_reset();\n  TIMER("exploit start");'
b = '  if (env_flag("SLIDE_ONLY", 0)) return 0;\n\n' + a
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('added SLIDE_ONLY early-return')
