#!/usr/bin/env python3
"""patch_task_alias.py

Sửa `task` của waiter (và waiter_task/pi_top_task trong trang) sang ĐỊA CHỈ HỢP LỆ
theo convention alias mà exploit đã dùng cho target fops: `data_addr(INIT_TASK)`.

Lý do (suy trực tiếp từ các lần treo):
  - route sơn `waiter->task = text_addr(INIT_TASK)`; với run `NO_SLIDE=1` thì
    `text_addr` cho ra địa chỉ KHÔNG-slide (kernel thật thì đã slide) => không hợp lệ.
  - chain[9] `if (!rt_mutex_owner(lock)) { if (prerequeue_top_waiter !=
    rt_mutex_top_waiter(lock)) wake_up_process(top_waiter->task); ... }` với owner=0
    (SSOPT_OWNER0=1) sẽ gọi wake_up_process(bogus_task) -> raw_spin_lock_irqsave(
    &bogus->pi_lock) với IRQ off => quay vô hạn => HARD LOCKUP (watchdog reset,
    không Oops, không dump) — đúng mọi run có owner0=1.
  - chain[11] cũng đọc `pi_task = W+0x30` rồi rt_mutex_setprio() -> cần địa chỉ
    task hợp lệ để đọc ->prio.

`data_addr(x)` = alias linear-map (đúng như `target=0xffffffc002bb1760` cho fops,
và như dòng log "init_task=ffffffc0029a9780").
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
n_t = s.count("text_addr(INIT_TASK)")
assert n_t >= 1, ("fops text_addr(INIT_TASK) count", n_t)
s = s.replace("text_addr(INIT_TASK)", "data_addr(INIT_TASK)")
open(F, "w").write(s)
print("fops.c: %d x text_addr(INIT_TASK) -> data_addr(INIT_TASK)" % n_t)

U = "/root/ghostlock/ghostlock-oneplus/src/core/util.c"
u = open(U).read()
n_u = u.count("text_addr(INIT_TASK)")
assert n_u >= 1, ("util text_addr(INIT_TASK) count", n_u)
u = u.replace("text_addr(INIT_TASK)", "data_addr(INIT_TASK)")
open(U, "w").write(u)
print("util.c: %d x text_addr(INIT_TASK) -> data_addr(INIT_TASK)" % n_u)
