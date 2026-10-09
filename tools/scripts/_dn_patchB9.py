#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()
old = """  setsid();
  setgid(0);
  setuid(0);

  int null_fd = open("/dev/null", O_RDWR);"""
new = """  setsid();
  setgid(0);
  setuid(0);

  /* Direct in-process proof that UMH ran us as root, independent of the
   * (KernelSU-oriented) shell script. */
  {
    int pf = open("/data/local/tmp/umh_root_proof",
                  O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (pf >= 0) {
      char b[192];
      int n = snprintf(b, sizeof(b),
                       "UMH ROOT uid=%d euid=%d gid=%d egid=%d pid=%d\\n",
                       getuid(), geteuid(), getgid(), getegid(), getpid());
      if (n > 0) { ssize_t wr = write(pf, b, n); (void)wr; }
      close(pf);
    }
    int lf = open("/data/local/tmp/.ghostlock_root.log",
                  O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (lf >= 0) {
      char b[192];
      int n = snprintf(b, sizeof(b), "UMH ROOT uid=%d euid=%d gid=%d\\n",
                       getuid(), geteuid(), getgid());
      if (n > 0) { ssize_t wr = write(lf, b, n); (void)wr; }
      close(lf);
    }
  }

  int null_fd = open("/dev/null", O_RDWR);"""
if s.count(old) != 1:
    print("FAIL: %d" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
