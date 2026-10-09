p = 'src/core/main.c'
s = open(p).read()

a = '''    pid_t rc = fork();
    if (rc == 0) {
      execl("/data/local/tmp/ghostlock32", "ghostlock32", "--route",
            b, t, v, m, (char *)NULL);
      pr_error("exec route child failed errno=%d\\n", errno);
      _exit(127);
    }'''
b = '''    /* ROUTE_SETSOCKOPT: the overlay no longer needs the 32-bit compat select
     * path, so the route child is the same 64-bit binary (native futex +
     * native setsockopt paint). */
    const char *route_bin = env_flag("ROUTE_SETSOCKOPT", 0)
                                ? "/data/local/tmp/ghostlock64r"
                                : "/data/local/tmp/ghostlock32";
    pid_t rc = fork();
    if (rc == 0) {
      execl(route_bin, route_bin, "--route", b, t, v, m, (char *)NULL);
      pr_error("exec route child %s failed errno=%d\\n", route_bin, errno);
      _exit(127);
    }'''
assert s.count(a) == 1, ('execl anchor', s.count(a))
s = s.replace(a, b, 1)
open(p, 'w').write(s)
print('main.c: route child path selected by ROUTE_SETSOCKOPT')
