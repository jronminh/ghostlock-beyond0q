/* glshell.c — same-process debug shell over the live configfs gadget.
 *
 * Entered by the driver right after the fops redirect is verified, while the
 * gadget is still installed. It lets you peek/poke kernel memory from adb
 * WITHOUT re-winning the flaky PI walk.
 *
 * Cross-process `glrw` was rejected: try_cfi_stage always restores the original
 * fops on exit, so a separate process cannot attach in time. Running in-process
 * keeps the gadget (and the memfd page that backs the fake fops table) alive.
 *
 * Protocol (file-based, so it works under `nohup ... </dev/null`):
 *   driver writes results  -> /data/local/tmp/gl.out
 *   user   writes a command-> /data/local/tmp/gl.cmd   (driver consumes+deletes)
 * Commands:
 *   peek  <hexaddr> [n]         n qwords (default 8)
 *   read  <hexaddr> <len>       hexdump len bytes
 *   write <hexaddr> <hexbytes>  write bytes (hex, no 0x)
 *   quit                        leave the shell
 * Auto-exits after ~10 min so a run cannot hang forever.
 */
#include <stdarg.h>
#include "common.h"

#define GL_CMD "/data/local/tmp/gl.cmd"
#define GL_OUT "/data/local/tmp/gl.out"

static int gl_out = -1;

static void gl_ofmt(const char *fmt, ...) {
  char b[512];
  va_list ap; va_start(ap, fmt);
  int n = vsnprintf(b, sizeof(b), fmt, ap);
  va_end(ap);
  if (n > 0 && gl_out >= 0) { ssize_t w = write(gl_out, b, n); (void)w; }
}

static void gl_hexdump(uintptr_t addr, const unsigned char *buf, size_t n) {
  for (size_t i = 0; i < n; i += 16) {
    gl_ofmt("%016llx: ", (unsigned long long)(addr + i));
    for (size_t j = 0; j < 16 && i + j < n; j++) gl_ofmt("%02x ", buf[i + j]);
    gl_ofmt("\n");
  }
}

static void gl_run_cmd(int fd, char *line) {
  char *cmd = strtok(line, " \t\r\n");
  if (!cmd) return;
  if (strcmp(cmd, "peek") == 0) {
    char *a = strtok(NULL, " \t\r\n"), *ns = strtok(NULL, " \t\r\n");
    if (!a) { gl_ofmt("peek: need <addr>\n"); return; }
    uintptr_t addr = (uintptr_t)strtoull(a, NULL, 0);
    long n = ns ? strtol(ns, NULL, 0) : 8;
    for (long i = 0; i < n; i++)
      gl_ofmt("%016llx = %016llx\n", (unsigned long long)(addr + 8 * i),
              (unsigned long long)kernel_read64(fd, addr + 8 * i));
  } else if (strcmp(cmd, "read") == 0) {
    char *a = strtok(NULL, " \t\r\n"), *ls = strtok(NULL, " \t\r\n");
    if (!a || !ls) { gl_ofmt("read: need <addr> <len>\n"); return; }
    uintptr_t addr = (uintptr_t)strtoull(a, NULL, 0);
    size_t len = strtoul(ls, NULL, 0);
    unsigned char *buf = malloc(len ? len : 1);
    ssize_t got = configfs_read_once(fd, addr, buf, len);
    gl_ofmt("read %zu -> %zd\n", len, got);
    if (got > 0) gl_hexdump(addr, buf, (size_t)got);
    free(buf);
  } else if (strcmp(cmd, "write") == 0) {
    char *a = strtok(NULL, " \t\r\n"), *h = strtok(NULL, " \t\r\n");
    if (!a || !h) { gl_ofmt("write: need <addr> <hexbytes>\n"); return; }
    uintptr_t addr = (uintptr_t)strtoull(a, NULL, 0);
    size_t hl = strlen(h), len = hl / 2;
    unsigned char *buf = malloc(len ? len : 1);
    for (size_t i = 0; i < len; i++) { unsigned v = 0; sscanf(h + 2 * i, "%2x", &v); buf[i] = (unsigned char)v; }
    ssize_t n = configfs_write_once(fd, addr, buf, len);
    gl_ofmt("write %zu -> %zd\n", len, n);
    free(buf);
  } else {
    gl_ofmt("cmds: peek <addr> [n] | read <addr> <len> | write <addr> <hex> | quit\n");
  }
}

int gl_shell_run(int fd) {
  gl_out = open(GL_OUT, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  gl_ofmt("== gl shell ready (fd=%d) — cmds: peek/read/write/quit ==\n", fd);
  if (gl_out >= 0) fsync(gl_out);
  int done = 0;
  for (int iter = 0; iter < 60000 && !done; iter++) {  /* ~10 min at 10 ms */
    int cf = open(GL_CMD, O_RDONLY);
    if (cf >= 0) {
      char line[512];
      ssize_t n = read(cf, line, sizeof(line) - 1);
      close(cf);
      if (n > 0) {
        line[n] = 0;
        unlink(GL_CMD);
        gl_ofmt("> %s", line);
        if (strncmp(line, "quit", 4) == 0) { gl_ofmt("bye\n"); done = 1; }
        else gl_run_cmd(fd, line);
        if (gl_out >= 0) fsync(gl_out);
      }
    }
    usleep(10000);
  }
  if (gl_out >= 0) { close(gl_out); gl_out = -1; }
  return 0;
}
