#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()

old = """    int lf = open("/data/local/tmp/.ghostlock_root.log",
                  O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (lf >= 0) {
      char b[192];
      int n = snprintf(b, sizeof(b), "UMH ROOT uid=%d euid=%d gid=%d\\n",
                       getuid(), geteuid(), getgid());
      if (n > 0) { ssize_t wr = write(lf, b, n); (void)wr; }
      close(lf);
    }
  }
"""
new = """    /* write from a static (kernel .rodata) buffer too: distinguishes a
     * copy_from_user/uaccess problem from the process being killed. */
    {
      static const char kb[] = "UMH-KERNEL-BUF\\n";
      int kf = open("/data/local/tmp/umh_static", O_WRONLY | O_CREAT | O_TRUNC, 0644);
      if (kf >= 0) { ssize_t wr = write(kf, kb, sizeof(kb) - 1); (void)wr; close(kf); }
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
"""
if s.count(old) != 1:
    print("FAIL static: %d" % s.count(old)); sys.exit(1)
s = s.replace(old, new)

old2 = """  execl("/system/bin/sh", "sh", "/data/local/tmp/.ghostlock_root.sh", NULL);
  _exit(127);"""
new2 = """  /* run the shell directly with an inline command as well */
  execl("/system/bin/sh", "sh", "-c",
        "id >/data/local/tmp/umh_id 2>&1; "
        "echo HI >/data/local/tmp/umh_hello; "
        "cat /proc/self/status >/data/local/tmp/umh_status 2>&1",
        (char *)NULL);
  execl("/system/bin/sh", "sh", "/data/local/tmp/.ghostlock_root.sh", NULL);
  _exit(127);"""
if s.count(old2) != 1:
    print("FAIL shell: %d" % s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

open(F, "w", encoding="utf-8").write(s)
print("ok")
