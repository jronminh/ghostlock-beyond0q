#!/usr/bin/env python3
"""patch_ssopt_v4.py

Ba sửa, đều suy từ bằng chứng vừa thu:
 1) LOG SỐNG SÓT PANIC: stdout đang bị block-buffer khi redirect ra file ⇒ mọi
    panic làm gl.log = 0 byte (QA/QA-delay0/QB/PB).  Đặt _IONBF ngay đầu main().
 2) TẠO PIPE HOLD TRƯỚC KHI SƠN: bản v3 tạo pipe()/fcntl() *sau* paint ⇒ chính
    các syscall đó (chuỗi sâu ~0x1b0) đè waiter.  Chuyển lên prologue route.
 3) Ghi rõ trong comment rằng hold phải là syscall DUY NHẤT sau paint.
"""
M = "/root/ghostlock/ghostlock-oneplus/src/core/main.c"
m = open(M).read()
old = """int main(int argc, char **argv) {"""
assert m.count(old) == 1, ("main", m.count(old))
new = """int main(int argc, char **argv) {
  /* The panic workflow depends on the log surviving an Oops: with stdout
   * redirected to a file it is block-buffered and everything printed between
   * flushes is lost (gl.log ended up 0 bytes after every crash). */
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);"""
m = m.replace(old, new, 1)
open(M, "w").write(m)
print("main.c: stdout/stderr unbuffered")

F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

# 1) create the hold pipe in the route prologue (before any paint)
old = """  struct timespec t0;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  int calls = 0, success = 0;
  for (int attempt = 1; attempt <= PSELECT_CFI_ROUTE_ATTEMPTS; attempt++) {"""
new = """  /* The in-kernel hold must not need ANY syscall after the paint (a syscall
   * would reuse this stack region).  Prepare the empty-pipe read end now, before
   * the first attempt. */
  if (ssopt_hold_r < 0) {
    int pfd[2];
    if (pipe(pfd) == 0) {
      if (pfd[0] >= 64) {
        int nb = fcntl(pfd[0], F_DUPFD, 3);
        if (nb >= 0 && nb < 64) { close(pfd[0]); pfd[0] = nb; }
      }
      ssopt_hold_r = pfd[0];
      ssopt_hold_w = pfd[1];
    }
    pr_info("ssopt hold pipe r=%d w=%d\\n", ssopt_hold_r, ssopt_hold_w);
  }

  struct timespec t0;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  int calls = 0, success = 0;
  for (int attempt = 1; attempt <= PSELECT_CFI_ROUTE_ATTEMPTS; attempt++) {"""
assert s.count(old) == 1, ("prologue", s.count(old))
s = s.replace(old, new, 1)

# 2) drop the in-attempt pipe creation
old = """    if (ssopt_hold_r < 0) {
      int pfd[2];
      if (pipe(pfd) == 0) {
        if (pfd[0] >= 64) {          /* keep the selected fd below nfds */
          int nb = fcntl(pfd[0], F_DUPFD, 3);
          if (nb >= 0 && nb < 64) { close(pfd[0]); pfd[0] = nb; }
        }
        ssopt_hold_r = pfd[0];
        ssopt_hold_w = pfd[1];
      }
    }
    if (ssopt_hold_r >= 0 && ssopt_hold_r < 64) {"""
new = """    if (ssopt_hold_r >= 0 && ssopt_hold_r < 64) {"""
assert s.count(old) == 1, ("in-attempt pipe", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: hold pipe created in the route prologue (nothing syscall-y after paint)")
