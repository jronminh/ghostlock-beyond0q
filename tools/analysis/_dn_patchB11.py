#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()
old = """  setsid();
  setgid(0);
  setuid(0);

  /* Direct in-process proof"""
new = """  setsid();
  setgid(0);
  setuid(0);

  /* Encode syscall results in filenames (open works, write appears not to). */
  {
    char sb[64];
    int n = snprintf(sb, sizeof(sb), "uid=%d euid=%d gid=%d", getuid(), geteuid(), getgid());
    char uf[128];
    snprintf(uf, sizeof(uf), "/data/local/tmp/umh_uid_%d_euid_%d_gid_%d",
             getuid(), geteuid(), getgid());
    int t = open(uf, O_WRONLY | O_CREAT, 0644); if (t >= 0) close(t);

    int f = open("/data/local/tmp/umh_w", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    errno = 0;
    ssize_t r = (f >= 0) ? write(f, sb, n) : -555; int e = errno;
    char wf[128];
    snprintf(wf, sizeof(wf), "/data/local/tmp/umh_wr_%ld_e%d", (long)r, e);
    int t2 = open(wf, O_WRONLY | O_CREAT, 0644); if (t2 >= 0) close(t2);
    if (f >= 0) close(f);

    int dn = open("/dev/null", O_WRONLY);
    errno = 0;
    ssize_t r2 = (dn >= 0) ? write(dn, sb, n) : -555; int e2 = errno;
    char df[128];
    snprintf(df, sizeof(df), "/data/local/tmp/umh_dn_%ld_e%d", (long)r2, e2);
    int t3 = open(df, O_WRONLY | O_CREAT, 0644); if (t3 >= 0) close(t3);
    if (dn >= 0) close(dn);
  }

  /* Direct in-process proof"""
if s.count(old) != 1:
    print("FAIL: %d" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok")
