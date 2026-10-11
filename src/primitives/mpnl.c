/*
 * mpnl.c - modprobe_path root helper + SELinux sync + localhost web UI.
 *
 * Runs as uid 0 (u:r:kernel:s0, full caps) via the modprobe_path helper channel.
 * Two control surfaces:
 *
 *   1. File channel (legacy, kept for scripts/back-compat):
 *        write a command to /data/local/tmp/rcmd -> run `sh -c <cmd>` as root ->
 *        output to /data/local/tmp/rout.  Do NOT delete rout/mp_ran (a
 *        kernel-spawned process cannot create new /data files; fscrypt ENOKEY)
 *        - pre-warm them.  `!senforce` re-runs the enforcement sync.
 *
 *   2. HTTP UI on 127.0.0.1:<GL_UI_PORT|8080>:
 *        serves an embedded single-page app (src/primitives/webui.html,
 *        generated into webui_html.h at build time) that drives root commands,
 *        setprop/getprop and `cmd`-based tweaks from Chrome on the device.
 *        The page is embedded because fscrypt forbids the daemon from creating
 *        new files under /data.  All /api/* calls require a per-boot random
 *        token (injected into the page) so a random same-device origin cannot
 *        silently drive root without reading the page first (CORS blocks that).
 *
 * SELinux: the exploit writes the raw `selinux_enforcing=0` and marks the
 * `kernel` type permissive in policydb.permissive_map (src/core/fops.c).  This
 * helper toggles /sys/fs/selinux/enforce 1 -> 0 once at start so the kernel
 * emits the real SELNL_MSG_SETENFORCE(0) notice and init's cached libselinux
 * AVC reloads -> property_service accepts setprop from this domain.
 * See docs/SELINUX_USERSYNC.md and docs/ROOT_UI.md.
 */
#define _GNU_SOURCE
#include <sys/wait.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <ctype.h>
#include <signal.h>

#include "webui_html.h"   /* unsigned char webui_html[]; unsigned int webui_html_len; */

#define GL_VERSION "rootui-1.0"
#define CHAN_DIR_DEFAULT "/data/local/tmp"

static char g_token[40];
static char g_dir[256];    /* channel dir: rcmd/rout/mp_ran (GL_CHANNEL_DIR) */
static char g_sh[128] = "/system/bin/sh";  /* command shell (GL_SH_PATH) */

static void logf_(const char *p, const char *s);

/* ------------------------------ small utils ------------------------------ */

/* stdio + channel files are all inherited from an odd place (the modprobe
 * helper's kernel-provided fds).  Force 0/1/2 onto /dev/null so pipe()/dup2()
 * in run_capture() can never collide with them, and so a command that reads
 * stdin does not eat the kernel's UMH socket. */
static void neutral_fds(void) {
  int dn = open("/dev/null", O_RDWR);
  if (dn < 0) return;
  dup2(dn, 0);
  dup2(dn, 1);
  dup2(dn, 2);
  if (dn > 2) close(dn);
}

static void chan_path(const char *name, char *out, size_t cap) {
  snprintf(out, cap, "%s/%s", g_dir, name);
}

static void chan_log(const char *msg) {
  char p[300];
  chan_path("mp_ran", p, sizeof(p));
  logf_(p, msg);
}


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

static void gen_token(void) {
  unsigned char b[16];
  memset(b, 0, sizeof(b));
  int f = open("/dev/urandom", O_RDONLY);
  if (f >= 0) { ssize_t r = read(f, b, sizeof(b)); (void)r; close(f); }
  for (int i = 0; i < 16; i++) snprintf(g_token + i * 2, 3, "%02x", b[i]);
  g_token[32] = 0;
}

/* read a whole small file, NUL-terminated, trailing CR/LF trimmed */
static int slurp(const char *path, char *out, size_t cap) {
  int f = open(path, O_RDONLY);
  if (f < 0) { out[0] = 0; return -1; }
  ssize_t n = read(f, out, cap - 1);
  close(f);
  if (n < 0) n = 0;
  out[n] = 0;
  while (n > 0 && (out[n-1] == '\n' || out[n-1] == '\r')) out[--n] = 0;
  return (int)n;
}

static void trim_eol(char *s) {
  size_t n = strlen(s);
  while (n > 0 && (s[n-1] == '\n' || s[n-1] == '\r' || s[n-1] == ' ')) s[--n] = 0;
}

static void write_all(int fd, const void *buf, size_t len) {
  const char *p = buf;
  while (len) {
    ssize_t n = send(fd, p, len, MSG_NOSIGNAL);
    if (n <= 0) { if (errno == EINTR) continue; break; }
    p += n; len -= (size_t)n;
  }
}

static void jstr(const char *s, char *out, size_t cap) {
  size_t o = 0;
  for (size_t i = 0; s[i] && o + 7 < cap; i++) {
    unsigned char c = (unsigned char)s[i];
    if (c == '"' || c == '\\') { out[o++] = '\\'; out[o++] = (char)c; }
    else if (c == '\n') { out[o++] = '\\'; out[o++] = 'n'; }
    else if (c == '\r') { out[o++] = '\\'; out[o++] = 'r'; }
    else if (c == '\t') { out[o++] = '\\'; out[o++] = 't'; }
    else if (c < 0x20) { o += (size_t)snprintf(out + o, cap - o, "\\u%04x", c); }
    else out[o++] = (char)c;
  }
  out[o] = 0;
}

static void urldecode(const char *s, char *out, size_t cap) {
  size_t o = 0;
  for (size_t i = 0; s[i] && o + 1 < cap; i++) {
    if (s[i] == '%' && isxdigit((unsigned char)s[i+1]) && isxdigit((unsigned char)s[i+2])) {
      char h[3] = { s[i+1], s[i+2], 0 };
      out[o++] = (char)strtol(h, NULL, 16); i += 2;
    } else if (s[i] == '+') out[o++] = ' ';
    else out[o++] = s[i];
  }
  out[o] = 0;
}

/* extract key=... from an urlencoded string (query or body) */
static int param(const char *q, const char *key, char *out, size_t cap) {
  out[0] = 0;
  if (!q || !*q) return 0;
  size_t kl = strlen(key);
  for (const char *p = q; p && *p; ) {
    if (strncmp(p, key, kl) == 0 && p[kl] == '=') {
      const char *v = p + kl + 1;
      const char *e = strchr(v, '&');
      size_t n = e ? (size_t)(e - v) : strlen(v);
      char tmp[4096];
      if (n >= sizeof(tmp)) n = sizeof(tmp) - 1;
      memcpy(tmp, v, n); tmp[n] = 0;
      urldecode(tmp, out, cap);
      return 1;
    }
    p = strchr(p, '&');
    if (p) p++;
  }
  return 0;
}

/* run `sh -c cmd` as root, capture combined stdout+stderr, return exit code */
static int run_capture(const char *cmd, char *out, size_t cap, int *rc) {
  int p[2];
  if (pipe(p) != 0) { if (rc) *rc = -1; if (cap) out[0] = 0; return -1; }
  /* lift both ends above the std fds so close(p[1]) can never kill a std fd */
  for (int i = 0; i < 2; i++) {
    if (p[i] <= 2) {
      int nf = fcntl(p[i], F_DUPFD, 3);
      if (nf >= 0) { close(p[i]); p[i] = nf; }
    }
  }
  pid_t pid = fork();
  if (pid == 0) {
    dup2(p[1], 1); dup2(p[1], 2);
    close(p[0]); close(p[1]);
    execl(g_sh, "sh", "-c", cmd, (char *)NULL);
    _exit(127);
  }
  close(p[1]);
  size_t used = 0;
  for (;;) {
    if (used >= cap - 1) break;
    ssize_t n = read(p[0], out + used, cap - 1 - used);
    if (n < 0) { if (errno == EINTR) continue; break; }
    if (n == 0) break;
    used += (size_t)n;
  }
  out[used] = 0;
  close(p[0]);
  int st = 0;
  while (waitpid(pid, &st, 0) < 0 && errno == EINTR) { }
  if (rc) *rc = WIFEXITED(st) ? WEXITSTATUS(st) : -1;
  return (int)used;
}

/* ------------------------------ HTTP layer ------------------------------- */

static void http_resp(int c, int code, const char *ctype, const char *body, size_t len) {
  char hdr[256];
  const char *reason = (code == 200) ? "OK" : (code == 403) ? "Forbidden"
                     : (code == 404) ? "Not Found" : (code == 400) ? "Bad Request" : "Error";
  int n = snprintf(hdr, sizeof(hdr),
      "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\n"
      "Cache-Control: no-store\r\nConnection: close\r\n\r\n",
      code, reason, ctype, len);
  write_all(c, hdr, (size_t)n);
  if (len) write_all(c, body, len);
}

static void json_out(int c, const char *obj) {
  http_resp(c, 200, "application/json", obj, strlen(obj));
}

static size_t build_page(char *o, size_t cap) {
  const char *TOK = "__GL_TOKEN__";
  const char *VER = "__GL_VERSION__";
  size_t tl = strlen(TOK), vl = strlen(VER), sl = strlen(g_token);
  size_t n = 0;
  for (size_t i = 0; i < webui_html_len && n + 64 < cap; ) {
    if (i + tl <= webui_html_len && memcmp(webui_html + i, TOK, tl) == 0) {
      memcpy(o + n, g_token, sl); n += sl; i += tl;
    } else if (i + vl <= webui_html_len && memcmp(webui_html + i, VER, vl) == 0) {
      memcpy(o + n, GL_VERSION, strlen(GL_VERSION)); n += strlen(GL_VERSION); i += vl;
    } else {
      o[n++] = (char)webui_html[i++];
    }
  }
  o[n] = 0;
  return n;
}

static void api_status(int c) {
  char ctx[160] = "?", enf[8] = "?", bid[80] = "?";
  slurp("/proc/self/attr/current", ctx, sizeof(ctx));
  slurp("/sys/fs/selinux/enforce", enf, sizeof(enf));
  slurp("/proc/sys/kernel/random/boot_id", bid, sizeof(bid));
  char c1[512], e1[32], b1[256];
  jstr(ctx, c1, sizeof(c1));
  jstr(enf, e1, sizeof(e1));
  jstr(bid, b1, sizeof(b1));
  char body[1024];
  snprintf(body, sizeof(body),
      "{\"gl\":true,\"version\":\"" GL_VERSION "\",\"uid\":%d,\"euid\":%d,"
      "\"gid\":%d,\"pid\":%d,\"ctx\":\"%s\",\"enforce\":\"%s\","
      "\"selinux\":\"%s\",\"boot_id\":\"%s\"}",
      getuid(), geteuid(), getgid(), getpid(), c1, e1,
      (strcmp(enf, "0") == 0) ? "Permissive" : "Enforcing", b1);
  json_out(c, body);
}

static void api_exec(int c, const char *cmd) {
  size_t cap = 128 * 1024;
  char *out = malloc(cap);
  if (!out) { http_resp(c, 500, "text/plain", "oom\n", 4); return; }
  int rc = -1;
  run_capture(cmd, out, cap, &rc);
  char *jb = malloc(strlen(out) * 2 + 64);
  if (!jb) { free(out); http_resp(c, 500, "text/plain", "oom\n", 4); return; }
  jstr(out, jb, strlen(out) * 2 + 64);
  char *resp = malloc(strlen(jb) + 64);
  if (!resp) { free(out); free(jb); http_resp(c, 500, "text/plain", "oom\n", 4); return; }
  sprintf(resp, "{\"rc\":%d,\"out\":\"%s\"}", rc, jb);
  json_out(c, resp);
  free(out); free(jb); free(resp);
}

static int valid_prop(const char *n) {
  if (!n || !*n || strlen(n) > 120) return 0;
  for (const char *p = n; *p; p++)
    if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '_' || *p == '-')) return 0;
  return 1;
}

static int valid_pkg(const char *n) {
  if (!n || !*n || strlen(n) > 128) return 0;
  for (const char *p = n; *p; p++)
    if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '_')) return 0;
  return 1;
}

static void api_prop(int c, const char *qs, const char *body) {
  char op[16] = "get", name[160] = "", value[1024] = "";
  param(qs, "op", op, sizeof(op));        param(body, "op", op, sizeof(op));
  param(qs, "name", name, sizeof(name));  param(body, "name", name, sizeof(name));
  param(qs, "value", value, sizeof(value)); param(body, "value", value, sizeof(value));
  if (!valid_prop(name)) { json_out(c, "{\"rc\":-1,\"out\":\"invalid name\"}"); return; }

  char out[4096] = ""; int rc = 0;
  if (strcmp(op, "set") == 0) {
    /* single-quote-escape the value; setprop is safeplace */
    char esc[2200]; size_t o = 0;
    for (size_t i = 0; value[i] && o + 5 < sizeof(esc); i++) {
      if (value[i] == '\'') { memcpy(esc + o, "'\\''", 4); o += 4; }
      else esc[o++] = value[i];
    }
    esc[o] = 0;
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "setprop '%s' '%s'", name, esc);
    run_capture(cmd, out, sizeof(out), &rc);        /* out = any error text */
    if (rc == 0) { char rd[256]; snprintf(rd, sizeof(rd), "getprop '%s'", name);
                   run_capture(rd, out, sizeof(out), NULL); }   /* out = read-back */
  } else {
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "getprop '%s'", name);
    run_capture(cmd, out, sizeof(out), &rc);
  }
  char jn[400], jv[4096];
  trim_eol(out);
  jstr(name, jn, sizeof(jn));
  jstr(out, jv, sizeof(jv));
  char resp[4600];
  snprintf(resp, sizeof(resp), "{\"rc\":%d,\"name\":\"%s\",\"value\":\"%s\"}", rc, jn, jv);
  json_out(c, resp);
}

static void api_pkg(int c, const char *qs, const char *body) {
  char op[16] = "list", pkg[192] = "";
  param(qs, "op", op, sizeof(op));   param(body, "op", op, sizeof(op));
  param(qs, "pkg", pkg, sizeof(pkg)); param(body, "pkg", pkg, sizeof(pkg));
  char cmd[512];
  if (strcmp(op, "list") == 0) {
    snprintf(cmd, sizeof(cmd), "cmd package list packages");
  } else if (strcmp(op, "disable") == 0 || strcmp(op, "enable") == 0) {
    if (!valid_pkg(pkg)) { json_out(c, "{\"rc\":-1,\"out\":\"invalid package\"}"); return; }
    if (strcmp(op, "disable") == 0)
      snprintf(cmd, sizeof(cmd), "cmd package disable-user --user 0 '%s' 2>&1", pkg);
    else
      snprintf(cmd, sizeof(cmd), "cmd package enable '%s' 2>&1", pkg);
  } else {
    json_out(c, "{\"rc\":-1,\"out\":\"bad op\"}"); return;
  }
  char *out = malloc(64 * 1024);
  if (!out) { http_resp(c, 500, "text/plain", "oom\n", 4); return; }
  int rc = 0;
  run_capture(cmd, out, 64 * 1024, &rc);
  char *jb = malloc(strlen(out) * 2 + 64);
  if (!jb) { free(out); http_resp(c, 500, "text/plain", "oom\n", 4); return; }
  jstr(out, jb, strlen(out) * 2 + 64);
  char *resp = malloc(strlen(jb) + 64);
  if (!resp) { free(out); free(jb); http_resp(c, 500, "text/plain", "oom\n", 4); return; }
  sprintf(resp, "{\"rc\":%d,\"out\":\"%s\"}", rc, jb);
  json_out(c, resp);
  free(out); free(jb); free(resp);
}

static void handle_client(int c) {
  struct timeval tv = { 6, 0 };
  setsockopt(c, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
  int one = 1;
  setsockopt(c, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

  char req[12288];
  size_t used = 0;
  char *hdr_end = NULL;
  while (used < sizeof(req) - 1) {
    ssize_t n = read(c, req + used, sizeof(req) - 1 - used);
    if (n <= 0) break;
    used += (size_t)n;
    req[used] = 0;
    hdr_end = strstr(req, "\r\n\r\n");
    if (hdr_end) break;
  }
  if (!hdr_end) { http_resp(c, 400, "text/plain", "bad request\n", 12); return; }

  size_t hlen = (size_t)(hdr_end - req) + 4;
  int clen = 0;
  char *cl = strcasestr(req, "Content-Length:");
  if (cl) clen = atoi(cl + 15);
  if (clen < 0) clen = 0;
  while (used - hlen < (size_t)clen && used < sizeof(req) - 1) {
    ssize_t n = read(c, req + used, sizeof(req) - 1 - used);
    if (n <= 0) break;
    used += (size_t)n;
    req[used] = 0;
  }
  const char *body = req + hlen;

  char method[8] = {0}, path[512] = {0};
  if (sscanf(req, "%7s %511s", method, path) != 2) {
    http_resp(c, 400, "text/plain", "bad request line\n", 18); return;
  }
  char *qs = strchr(path, '?');
  if (qs) { *qs = 0; qs++; }

  /* serve the page without a token (it carries the token for same-origin use) */
  if (strcmp(path, "/") == 0 || strcmp(path, "/index.html") == 0) {
    char *page = malloc(webui_html_len + 512);
    if (!page) { http_resp(c, 500, "text/plain", "oom\n", 4); return; }
    size_t n = build_page(page, webui_html_len + 512);
    http_resp(c, 200, "text/html; charset=utf-8", page, n);
    free(page);
    return;
  }

  if (strncmp(path, "/api/", 5) != 0) { http_resp(c, 404, "text/plain", "not found\n", 10); return; }

  /* token check: header X-GL-Token, or ?t= / body t= */
  char htok[64] = "";
  char *th = strcasestr(req, "X-GL-Token:");
  if (th) {
    th += 11;
    while (*th == ' ') th++;
    size_t i = 0;
    while (th[i] && th[i] != '\r' && th[i] != '\n' && i < sizeof(htok) - 1) { htok[i] = th[i]; i++; }
    htok[i] = 0;
  }
  if (!htok[0]) param(qs, "t", htok, sizeof(htok));
  if (!htok[0]) param(body, "t", htok, sizeof(htok));
  if (strcmp(htok, g_token) != 0) { http_resp(c, 403, "text/plain", "forbidden\n", 10); return; }

  if (strcmp(path, "/api/status") == 0) { api_status(c); return; }
  if (strcmp(path, "/api/exec") == 0) {
    char cmd[8192];
    if (!param(body, "cmd", cmd, sizeof(cmd))) param(qs, "cmd", cmd, sizeof(cmd));
    if (!cmd[0]) { json_out(c, "{\"rc\":-1,\"out\":\"no cmd\"}"); return; }
    api_exec(c, cmd);
    return;
  }
  if (strcmp(path, "/api/prop") == 0) { api_prop(c, qs, body); return; }
  if (strcmp(path, "/api/pkg") == 0) { api_pkg(c, qs, body); return; }
  http_resp(c, 404, "text/plain", "not found\n", 10);
}

/* ------------------------- file command channel -------------------------- */

static void poll_rcmd(void) {
  char p_rcmd[300], p_rout[300];
  chan_path("rcmd", p_rcmd, sizeof(p_rcmd));
  chan_path("rout", p_rout, sizeof(p_rout));
  int rf = open(p_rcmd, O_RDONLY);
  if (rf < 0) return;
  char cmd[1024];
  ssize_t n = read(rf, cmd, sizeof(cmd) - 1);
  close(rf);
  if (n <= 0) return;
  cmd[n] = 0;
  while (n > 0 && (cmd[n-1] == '\n' || cmd[n-1] == '\r')) cmd[--n] = 0;
  if (n == 0) return;
  if (strncmp(cmd, "!senforce", 9) == 0) {
    sync_selinux();
    int of = open(p_rout, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (of >= 0) { ssize_t w = write(of, "selinux resync\n", 15); (void)w; close(of); }
  } else {
    char *out = malloc(128 * 1024);
    int rc = 0;
    if (out) run_capture(cmd, out, 128 * 1024, &rc);
    int of = open(p_rout, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (of >= 0) {
      if (out) { ssize_t w = write(of, out, strlen(out)); (void)w; }
      char tb[64];
      int tn = snprintf(tb, sizeof(tb), "\n[rc=%d]\n", rc);
      if (tn > 0) { ssize_t w = write(of, tb, (size_t)tn); (void)w; }
      close(of);
    }
    free(out);
  }
  int tf = open(p_rcmd, O_WRONLY | O_TRUNC);
  if (tf >= 0) close(tf);
}

static void serve_http(int port) {
  int ls = socket(AF_INET, SOCK_STREAM, 0);
  if (ls < 0) return;
  int one = 1;
  setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
  struct sockaddr_in sa;
  memset(&sa, 0, sizeof(sa));
  sa.sin_family = AF_INET;
  sa.sin_port = htons((uint16_t)port);
  sa.sin_addr.s_addr = htonl(0x7f000001);   /* loopback only */
  if (bind(ls, (struct sockaddr *)&sa, sizeof(sa)) != 0) {
    char b[128];
    int n = snprintf(b, sizeof(b), "rootui: bind %d failed: %s\n", port, strerror(errno));
    if (n > 0) chan_log(b);
    return;
  }
  if (listen(ls, 8) != 0) return;

  {
    char b[64];
    int n = snprintf(b, sizeof(b), "rootui: listening 127.0.0.1:%d\n", port);
    if (n > 0) chan_log(b);
  }
  for (;;) {
    fd_set rf;
    FD_ZERO(&rf);
    FD_SET(ls, &rf);
    struct timeval tv = { 0, 300000 };
    int r = select(ls + 1, &rf, NULL, NULL, &tv);
    if (r > 0 && FD_ISSET(ls, &rf)) {
      int c = accept(ls, NULL, NULL);
      if (c >= 0) { handle_client(c); close(c); }
    } else if (r < 0 && errno != EINTR) {
      usleep(100000);
    }
    poll_rcmd();
  }
}

/* --------------------------------- main ---------------------------------- */

int main(int argc, char **argv) {
  (void)argc; (void)argv;
  signal(SIGPIPE, SIG_IGN);
  setgid(0);
  setuid(0);
  gen_token();

  const char *ce = getenv("GL_CHANNEL_DIR");
  snprintf(g_dir, sizeof(g_dir), "%s", (ce && *ce) ? ce : CHAN_DIR_DEFAULT);
  const char *se = getenv("GL_SH_PATH");
  if (se && *se) snprintf(g_sh, sizeof(g_sh), "%s", se);

  char p_ran[300];
  chan_path("mp_ran", p_ran, sizeof(p_ran));
  int f = open(p_ran, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (f >= 0) {
    char b[192];
    int n = snprintf(b, sizeof(b), "mpnl uid=%d euid=%d gid=%d pid=%d ver=%s\n",
                     getuid(), geteuid(), getgid(), getpid(), GL_VERSION);
    if (n > 0) { ssize_t w = write(f, b, n); (void)w; }
    close(f);
  }

  pid_t d = fork();
  if (d == 0) {
    setsid();
    neutral_fds();
    sync_selinux();
    char ev = '?';
    int e0 = open("/sys/fs/selinux/enforce", O_RDONLY);
    if (e0 >= 0) { ssize_t r = read(e0, &ev, 1); (void)r; close(e0); }
    char m[96];
    snprintf(m, sizeof(m), "selinux sync done; enforce now=%c\n", ev);
    chan_log(m);

    int port = 8080;
    const char *pe = getenv("GL_UI_PORT");
    if (pe && *pe) port = atoi(pe);
    serve_http(port);
  }
  return 0;
}
