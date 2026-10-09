#!/usr/bin/env python3
import sys, os
CORE = os.path.expanduser("~/ghostlock/ghostlock-oneplus/src/core")

def patch(path, old, new):
    p = os.path.join(CORE, path)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        print("FAIL %s: %d occurrences of %r" % (path, s.count(old), old[:100])); sys.exit(1)
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    print("ok  %s" % path)

# 1. fops.c: optional UMH bypass for diagnostics
patch("fops.c",
      "  if (install_umh_root(fd)) return 1;\n"
      "  return install_android_root(fd);\n",
      "  if (!env_flag(\"SKIP_UMH\", 0)) {\n"
      "    if (install_umh_root(fd)) return 1;\n"
      "  }\n"
      "  return install_android_root(fd);\n")

# 2. umh_root.c: per-step tracing
patch("umh_root.c",
      "  uintptr_t selinux_addr = data_addr(SELINUX_ENFORCING);\n"
      "  uint8_t permissive = 0;\n"
      "  if (!pipe_phys_write_data(fd, selinux_addr,\n"
      "                            &permissive, sizeof(permissive))) {\n"
      "    pr_error(\"umh: selinux write failed\\n\");\n"
      "    return 0;\n"
      "  }\n",
      "  uintptr_t selinux_addr = data_addr(SELINUX_ENFORCING);\n"
      "  uint8_t permissive = 0;\n"
      "  pr_info(\"umh: step1 selinux addr=%016zx\\n\", (size_t)selinux_addr);\n"
      "  fsync(1);\n"
      "  if (!pipe_phys_write_data(fd, selinux_addr,\n"
      "                            &permissive, sizeof(permissive))) {\n"
      "    pr_error(\"umh: selinux write failed\\n\");\n"
      "    return 0;\n"
      "  }\n"
      "  pr_info(\"umh: step1 selinux write ok\\n\");\n"
      "  fsync(1);\n")

patch("umh_root.c",
      "  uintptr_t wq_slot = data_addr(wq_image);\n"
      "  uintptr_t wq = umh_read64(fd, wq_slot);\n"
      "  uintptr_t pwq = umh_read64(fd, wq + WQ_DFL_PWQ_OFF);\n"
      "  uintptr_t pool = umh_read64(fd, pwq + PWQ_POOL_OFF);\n"
      "  uintptr_t pwq_wq = umh_read64(fd, pwq + PWQ_WQ_OFF);\n",
      "  uintptr_t wq_slot = data_addr(wq_image);\n"
      "  pr_info(\"umh: step2 wq_slot=%016zx dfl_pwq_off=%#x\\n\",\n"
      "          (size_t)wq_slot, (unsigned)WQ_DFL_PWQ_OFF);\n"
      "  fsync(1);\n"
      "  uintptr_t wq = umh_read64(fd, wq_slot);\n"
      "  pr_info(\"umh: step2 wq=%016zx\\n\", (size_t)wq);\n"
      "  fsync(1);\n"
      "  uintptr_t pwq = umh_read64(fd, wq + WQ_DFL_PWQ_OFF);\n"
      "  pr_info(\"umh: step2 pwq=%016zx\\n\", (size_t)pwq);\n"
      "  fsync(1);\n"
      "  uintptr_t pool = umh_read64(fd, pwq + PWQ_POOL_OFF);\n"
      "  uintptr_t pwq_wq = umh_read64(fd, pwq + PWQ_WQ_OFF);\n"
      "  pr_info(\"umh: step2 pool=%016zx pwq_wq=%016zx\\n\",\n"
      "          (size_t)pool, (size_t)pwq_wq);\n"
      "  fsync(1);\n")
print("done")
