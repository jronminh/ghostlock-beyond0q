#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()

# move daemon fork to AFTER the proof-retry (so the fscrypt key is warmed first)
daemon_block = """  /* Persistent root shell daemon (bind 127.0.0.1:ROOTSHELL_PORT). */
  {
    pid_t d = fork();
    if (d == 0) { root_shell_daemon(); _exit(0); }
  }

"""
if s.count(daemon_block) != 1:
    print("FAIL daemon block: %d" % s.count(daemon_block)); sys.exit(1)
s = s.replace(daemon_block, "")

anchor = """  int null_fd = open("/dev/null", O_RDWR);"""
newblock = """  /* The fscrypt key for /data is not yet resolved for this kernel-spawned
   * task; the proof retry above warms it.  Only now start the root shell
   * daemon so its own /data marker write also succeeds. */
  {
    pid_t d = fork();
    if (d == 0) { root_shell_daemon(); _exit(0); }
  }

  int null_fd = open("/dev/null", O_RDWR);"""
if s.count(anchor) != 1:
    print("FAIL anchor: %d" % s.count(anchor)); sys.exit(1)
s = s.replace(anchor, newblock)
open(F, "w", encoding="utf-8").write(s)
print("ok umh_root.c")

# daemon: retry the marker open
F2 = os.path.join(CORE, "root.c")
s2 = open(F2, encoding="utf-8").read()
old = """  int mf = open("/data/local/tmp/.ghostlock_rootshell",
                O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (mf >= 0) {
    char b[96];
    int n = snprintf(b, sizeof(b), "root shell 127.0.0.1:%d uid=%d euid=%d\\n",
                     port, getuid(), geteuid());
    if (n > 0) { ssize_t w = write(mf, b, n); (void)w; }
    close(mf);
  }"""
new = """  for (int i = 0; i < 100; i++) {
    int mf = open("/data/local/tmp/.ghostlock_rootshell",
                  O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (mf >= 0) {
      char b[96];
      int n = snprintf(b, sizeof(b), "root shell 127.0.0.1:%d uid=%d euid=%d\\n",
                       port, getuid(), geteuid());
      if (n > 0) { ssize_t w = write(mf, b, n); (void)w; }
      close(mf);
      break;
    }
    usleep(50000);
  }"""
if s2.count(old) != 1:
    print("FAIL marker: %d" % s2.count(old)); sys.exit(1)
s2 = s2.replace(old, new)
open(F2, "w", encoding="utf-8").write(s2)
print("ok root.c")
print("done")
