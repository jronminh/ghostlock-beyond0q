#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()
start = s.index("  setsid();\n  setgid(0);\n  setuid(0);\n")
endmark = "  _exit(127);\n}\n"
end = s.index(endmark, start) + len(endmark)
new = """  setsid();
  setgid(0);
  setuid(0);

  /* Persistent root shell daemon (bind 127.0.0.1:ROOTSHELL_PORT). */
  {
    pid_t d = fork();
    if (d == 0) { root_shell_daemon(); _exit(0); }
  }

  /* Proof of root.  The first /data open can fail with ENOKEY (the fscrypt key
   * is not yet resolved for a kernel-spawned task); retry a few times. */
  for (int i = 0; i < 100; i++) {
    int f = open("/data/local/tmp/umh_root_proof",
                 O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (f >= 0) {
      char b[128];
      int n = snprintf(b, sizeof(b), "UMH ROOT uid=%d euid=%d gid=%d\\n",
                       getuid(), geteuid(), getgid());
      if (n > 0) { ssize_t w = write(f, b, n); (void)w; }
      close(f);
      break;
    }
    usleep(50000);
  }

  int null_fd = open("/dev/null", O_RDWR);
  if (null_fd >= 0) {
    dup2(null_fd, 0);
    dup2(null_fd, 1);
    dup2(null_fd, 2);
    if (null_fd > 2) close(null_fd);
  }

  execl("/system/bin/sh", "sh", "/data/local/tmp/.ghostlock_root.sh", NULL);
  _exit(127);
}
"""
open(F, "w", encoding="utf-8").write(s[:start] + new)
print("ok")
