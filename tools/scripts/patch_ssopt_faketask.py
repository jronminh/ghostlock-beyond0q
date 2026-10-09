#!/usr/bin/env python3
"""patch_ssopt_faketask.py

SSOPT_FAKE_TASK=1 : waiter->task = fake_task (địa chỉ TRANG GIẢ, chắc chắn map
được) thay vì INIT_TASK, và pi_top_task/waiter_task trong trang cũng = fake_task
=> không còn phụ thuộc địa chỉ image/alias cho `task`, và điều kiện early-exit
`p->pi_top_task == pi_task` khớp nhau.

Dùng kèm WRITE4_SCRATCH=1 (util.c) để đích ghi PI nằm trong chính trang giả
(RIGHT_OFF slot) => phép thử "đường ghi có chạy" thuần, không dính alias .data.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = "pselect_custom_write_enabled() ? fake_task\n                                                      : data_addr(INIT_TASK)"
n = s.count(old)
if n == 0:
    old = "pselect_custom_write_enabled() ? fake_task : data_addr(INIT_TASK)"
    n = s.count(old)
new = "ssopt_fake_task_enabled() ? fake_task : data_addr(INIT_TASK)"
assert n >= 1, ("fops task ternary", n)
s = s.replace(old, new)
# declare the helper
old2 = "int sock_paint_fd = -1;"
new2 = ("int sock_paint_fd = -1;\n\n"
        "/* SSOPT_FAKE_TASK=1: use the fake page as the waiter's task */\n"
        "static int ssopt_fake_task_enabled(void) {\n"
        "  return pselect_custom_write_enabled() || env_flag(\"SSOPT_FAKE_TASK\", 0);\n"
        "}")
assert s.count(old2) == 1, ("decl", s.count(old2))
s = s.replace(old2, new2, 1)
open(F, "w").write(s)
print("fops.c: %d task ternary -> ssopt_fake_task_enabled()" % n)

U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()
old3 = """  uint64_t waiter_task = data_addr(INIT_TASK);"""
new3 = """  uint64_t waiter_task = env_flag("SSOPT_FAKE_TASK", 0) ? fake_task
                                                        : data_addr(INIT_TASK);"""
assert u.count(old3) == 1, ("waiter_task", u.count(old3))
u = u.replace(old3, new3, 1)
old4 = """  uint64_t pi_top_task = data_addr(INIT_TASK);"""
new4 = """  uint64_t pi_top_task = env_flag("SSOPT_FAKE_TASK", 0) ? fake_task
                                                        : data_addr(INIT_TASK);"""
assert u.count(old4) == 1, ("pi_top_task", u.count(old4))
u = u.replace(old4, new4, 1)
open(U, "w").write(u)
print("util.c: waiter_task/pi_top_task follow SSOPT_FAKE_TASK")
