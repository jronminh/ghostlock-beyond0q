#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")
F = os.path.join(CORE, "root.c")
s = open(F, encoding="utf-8").read()

# 1. don't read garbage for the selinux cred blob offset (off_selinux_blob_sizes==0)
old1 = "  selinux_cred_blob_off =\n    pipe_read32(fd, data_addr(SELINUX_BLOB_SIZES));\n"
new1 = ("  /* SELinux cred blob lives at cred->security + 0 on this kernel; the\n"
        "   * selinux_blob_sizes symbol offset is unavailable (0), so reading it\n"
        "   * would pull garbage out of .text and cause a wild write. */\n"
        "  selinux_cred_blob_off = 0;\n")
if s.count(old1) != 1:
    print("FAIL1: %d" % s.count(old1)); sys.exit(1)
s = s.replace(old1, new1)

# 2. skip the SID patch (SELinux is permissive once we zero selinux_enforcing)
old2 = "  return patch_cred_identity(fd, cred) && patch_cred_sid(fd, cred);\n"
new2 = ("  /* SID patch omitted: SELinux is set permissive, and the cred blob SID\n"
        "   * offset is not reliable here. */\n"
        "  return patch_cred_identity(fd, cred);\n")
if s.count(old2) != 1:
    print("FAIL2: %d" % s.count(old2)); sys.exit(1)
s = s.replace(old2, new2)

open(F, "w", encoding="utf-8").write(s)
print("ok")
