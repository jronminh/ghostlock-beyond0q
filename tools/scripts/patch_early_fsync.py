#!/usr/bin/env python3
"""patch_early_fsync.py

Các dòng log TRƯỚC khi vào route còn nằm trong buffer stdio; nếu tiến trình bị
kill (timeout) hoặc treo trước đó thì gl.log = 0 byte, không biết nó dừng ở đâu.
Thêm fsync(1) ngay:
  - cuối log_startup_context()  (in kernel/offsets/context/limits/config/bridge)
  - ngay sau prepare_perf_fake_page() (in base/lock/task/fops)
=> lần chạy sau luôn biết exploit tới được bước nào.
"""
U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()

# 1) log_startup_context: thêm fsync ở cuối hàm
import re
m = re.search(r"void log_startup_context\(void\) \{.*?\n\}\n", u, re.S)
assert m, "log_startup_context not found"
body = m.group(0)
new_body = body[:-3] + "  log_sync();   /* survive a later kill/panic */\n}\n"
u = u[:m.start()] + new_body + u[m.end():]

# 2) prepare_perf_fake_page: fsync sau dòng "prepare_perf_fake_page ok"
old = """  pr_info("prepare_perf_fake_page ok base=%016zx lock=%016zx task=%016zx fops=%016zx\\n",
          base, fake_lock, fake_task, fake_fops);
  return base;"""
new = """  pr_info("prepare_perf_fake_page ok base=%016zx lock=%016zx task=%016zx fops=%016zx\\n",
          base, fake_lock, fake_task, fake_fops);
  log_sync();
  return base;"""
assert u.count(old) == 1, ("prepare log", u.count(old))
u = u.replace(old, new, 1)
open(U, "w").write(u)
print("util.c: +fsync at end of log_startup_context and after fake page prepare")
