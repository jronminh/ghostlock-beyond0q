#!/usr/bin/env python3
"""patch_ssopt_quiet_exit.py

Triệt tiêu đường thoát syscall đè lên dangling waiter.

Sự thật đo được (kpPB/kpr/kpP): panic `rb_erase_cached+0x20` với
waiter->tree_entry.rb_right = rác high-entropy (một cặp saved-PC kiểu
`stp x29,x16,[sp,#k]` của kernel), dù T không phát syscall nào sau paint.

⇒ Thủ phạm là CHÍNH đường thoát của lệnh paint:
   ret_to_user -> work_pending -> do_notify_resume()  (chạy khi TIF_SIGPENDING
   hoặc TIF_NOTIFY_RESUME); frame vào ở SP0-0x190 nên cặp saved đè SP0-0x188..
   0x179 (waiter->task@0x30), còn task_work callback đi sâu hơn — đúng vùng
   waiter+0x08/+0x10.

Sửa (nhỏ, suy từ ret_to_user/signal.h):
  - chặn mọi signal chặn được  => recalc_sigpending() xoá TIF_SIGPENDING;
  - một lần trả về userspace (syscall getpid) => do_notify_resume chạy hết
    task_work đang treo TRƯỚC khi sơn.
Sau đó đường thoát của chính setsockopt() không còn việc để làm ⇒ paint
(đủ 8 word) sống nguyên tới lúc consumer walk.

Thêm: include <signal.h>.
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()

old = """#include "common.h"
#include "runtime_struct_offsets.h"
#include <time.h>"""
new = """#include "common.h"
#include "runtime_struct_offsets.h"
#include <time.h>
#include <signal.h>"""
assert s.count(old) == 1, ("include", s.count(old))
s = s.replace(old, new, 1)

old = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf);
    errno = 0;"""
new = """    pr_info("ssopt pre paint +%.0fms attempt=%d task=%016zx lock=%016zx len=%zu\\n",
            fops_elapsed_ms(&t0), attempt, fake_task, fake_lock, sizeof buf);
    /* The dangling waiter lives on THIS thread's kernel stack (SP0-0x1b0).
     * ret_to_user -> work_pending -> do_notify_resume() runs AFTER our paint
     * whenever TIF_SIGPENDING / TIF_NOTIFY_RESUME is set; its frame (entry sp
     * = SP0-0x190) writes a saved x29/x16 pair over SP0-0x188..0x179 (that is
     * waiter->task@0x30 and the top of waiter->lock@0x38), and task_work
     * callbacks reach waiter+0x08/+0x10 -- exactly the high-entropy garbage
     * seen in kpr/kpP/kpPB (rb_erase_cached+0x20 with a bogus rb_right).
     * Block every blockable signal (recalc_sigpending() then clears
     * TIF_SIGPENDING) and make one return-to-userspace so pending task_work is
     * flushed BEFORE the paint: the setsockopt() exit path then has no work to
     * run and the painted waiter survives until the consumer's walk. */
    {
      static int ssopt_exit_quiet;
      if (!ssopt_exit_quiet) {
        sigset_t all;
        sigfillset(&all);
        pthread_sigmask(SIG_BLOCK, &all, NULL);
        ssopt_exit_quiet = 1;
      }
      (void)syscall(SYS_getpid);
    }
    errno = 0;"""
assert s.count(old) == 1, ("quiet exit", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: flush task_work + block signals right before the paint")
