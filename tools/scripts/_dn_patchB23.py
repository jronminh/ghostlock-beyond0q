#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")

def patch(path, old, new, cnt=1):
    p = os.path.join(CORE, path)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != cnt:
        print("FAIL %s: %d (want %d)" % (path, s.count(old), cnt)); sys.exit(1)
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok  %s" % path)

# 1. expose root_shell_daemon
patch("root.c",
      "static void root_shell_daemon(void) {",
      "void root_shell_daemon(void) {")
patch("common.h",
      "int install_android_root(int fd);\n",
      "int install_android_root(int fd);\nvoid root_shell_daemon(void);\n")

# 2. UMH handler: become root, write proof (retry open), start the root shell daemon
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()
old = """  setsid();
  setgid(0);
  setuid(0);

  /* Direct in-process proof that UMH ran us as root, independent of the
   * (KernelSU-oriented) shell script. */"""
new = """  setsid();
  setgid(0);
  setuid(0);

  /* Start the persistent root shell daemon (bind 127.0.0.1:ROOTSHELL_PORT). */
  {
    pid_t d = fork();
    if (d == 0) { root_shell_daemon(); _exit(0); }
  }

  /* Proof of root; the first /data open can fail with ENOKEY (fscrypt key not
   * yet resolved for this kernel-spawned task), so retry. */
  for (int i = 0; i < 100; i++) {
    int f = open("/data/local/tmp/.ghostlock_umh_proof",
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

  /* Direct in-process proof that UMH ran us as root, independent of the
   * (KernelSU-oriented) shell script. */"""
if s.count(old) != 1:
    print("FAIL umh: %d" % s.count(old)); sys.exit(1)
open(F, "w", encoding="utf-8").write(s.replace(old, new))
print("ok  umh_root.c")
print("done")
