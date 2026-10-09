#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "umh_root.c")
s = open(F, encoding="utf-8").read()

start = s.index("  /* Encode syscall results in filenames")
endmark = "    if (dn >= 0) close(dn);\n  }\n"
end = s.index(endmark, start) + len(endmark)

new = """  /* Encode syscall results in filenames. */
  {
    errno = 0;
    int f = open("/data/local/tmp/umh_w2", O_WRONLY | O_CREAT, 0644);
    int oe = errno;
    errno = 0;
    ssize_t r = (f >= 0) ? write(f, "HELLO-WORLD\\n", 12) : -555;
    int we = errno;
    if (f >= 0) close(f);
    char wf[160];
    snprintf(wf, sizeof(wf),
             "/data/local/tmp/umh_W_fd%d_oe%d_ret%ld_we%d_uid%d_fsuid%d",
             f, oe, (long)r, we, getuid(), (int)setfsuid(getuid()));
    int t2 = open(wf, O_WRONLY | O_CREAT, 0644); if (t2 >= 0) close(t2);

    errno = 0;
    int f2 = open("/data/local/tmp/umh_w3", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    int oe2 = errno;
    if (f2 >= 0) close(f2);
    char wf2[160];
    snprintf(wf2, sizeof(wf2), "/data/local/tmp/umh_TRUNC_fd%d_oe%d", f2, oe2);
    int t3 = open(wf2, O_WRONLY | O_CREAT, 0644); if (t3 >= 0) close(t3);
  }
"""
s = s[:start] + new + s[end:]
open(F, "w", encoding="utf-8").write(s)
print("ok")
