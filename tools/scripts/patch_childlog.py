p = 'src/core/main.c'
s = open(p).read()
a = '''  setvbuf(stdout, NULL, _IONBF, 0);
  route_only_mode = 1;
  if (select_offsets() < 0) return 1;'''
b = '''  setvbuf(stdout, NULL, _IONBF, 0);
  route_only_mode = 1;
  {
    int lf = open("/data/local/tmp/rchild.log",
                  O_WRONLY | O_CREAT | O_TRUNC | O_SYNC, 0644);
    if (lf >= 0) { dup2(lf, 1); dup2(lf, 2); if (lf > 2) close(lf); }
  }
  if (select_offsets() < 0) return 1;'''
assert s.count(a) == 1, s.count(a)
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('child logs to /data/local/tmp/rchild.log (O_SYNC)')
