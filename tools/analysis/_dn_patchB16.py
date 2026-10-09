#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "root.c")
s = open(F, encoding="utf-8").read()

# includes
if "#include <netinet/in.h>" not in s:
    s = s.replace('#include "runtime_struct_offsets.h"\n',
                  '#include "runtime_struct_offsets.h"\n'
                  '#include <netinet/in.h>\n#include <arpa/inet.h>\n#include <sys/socket.h>\n', 1)

# daemon function (insert before spawn_root_child)
anchor = "int spawn_root_child(void) {"
daemon = '''/*
 * Root shell daemon.  Runs in a grandchild of the (cred-patched) root child, so
 * it is a normal uid-0 process with a working /data keyring and full I/O.
 * Reach it from a PC with:  adb forward tcp:2223 tcp:2223 ; nc 127.0.0.1 2223
 */
static void root_shell_daemon(void) {
  int port = 2223;
  const char *pe = getenv("ROOTSHELL_PORT");
  if (pe && *pe) port = atoi(pe);

  setsid();
  int s = socket(AF_INET, SOCK_STREAM, 0);
  if (s < 0) return;
  int one = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
  struct sockaddr_in sa;
  memset(&sa, 0, sizeof(sa));
  sa.sin_family = AF_INET;
  sa.sin_port = htons((uint16_t)port);
  sa.sin_addr.s_addr = htonl(0x7f000001);
  if (bind(s, (struct sockaddr *)&sa, sizeof(sa)) != 0) return;
  if (listen(s, 8) != 0) return;

  int mf = open("/data/local/tmp/.ghostlock_rootshell",
                O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (mf >= 0) {
    char b[96];
    int n = snprintf(b, sizeof(b), "root shell 127.0.0.1:%d uid=%d euid=%d\\n",
                     port, getuid(), geteuid());
    if (n > 0) { ssize_t w = write(mf, b, n); (void)w; }
    close(mf);
  }

  for (;;) {
    int c = accept(s, NULL, NULL);
    if (c < 0) continue;
    pid_t p = fork();
    if (p == 0) {
      dup2(c, 0); dup2(c, 1); dup2(c, 2);
      if (c > 2) close(c);
      close(s);
      execl("/system/bin/sh", "sh", "-i", (char *)NULL);
      _exit(127);
    }
    close(c);
    while (waitpid(-1, NULL, WNOHANG) > 0) { }
  }
}

'''
if s.count(anchor) != 1:
    print("FAIL anchor: %d" % s.count(anchor)); sys.exit(1)
s = s.replace(anchor, daemon + anchor, 1)

# spawn the daemon once the child is root
old = """    report.su_daemon_pid = -1;
    if (report.setgid_ret == 0 && report.setuid_ret == 0) {"""
new = """    report.su_daemon_pid = -1;
    if (report.setgid_ret == 0 && report.setuid_ret == 0) {
      /* grandchild becomes the persistent root shell daemon */
      pid_t gc = fork();
      if (gc == 0) {
        root_shell_daemon();
        _exit(0);
      }
    }
    if (report.setgid_ret == 0 && report.setuid_ret == 0) {"""
if s.count(old) != 1:
    print("FAIL spawn: %d" % s.count(old)); sys.exit(1)
s = s.replace(old, new)

open(F, "w", encoding="utf-8").write(s)
print("ok")
