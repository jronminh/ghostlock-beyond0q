# PANIC_CAUSE.md — why the walk kernel-panics

Analysis only (no device runs). Sources: recovered old-session notes
(`recovered/…/notes.md`), the session patch chain (`tools/scripts/_dn_patchB*.py`),
and the current `src/`.

## TL;DR

The single PI write happens by making the kernel walk a **dangling
`rt_mutex_waiter` that lives on thread T's kernel stack** at `SP0-0x1b0`. We
"paint" it from userspace with `setsockopt(...,1000,...)`, but the paint is
**overwritten within microseconds** before the consumer's `sched_setattr(T)` walk
reads it — by an IRQ taken at EL0 (T is spinning in userspace) and/or by the syscall
exit path. The walk then does `rb_erase_cached()` on garbage children ⇒
`Oops` (or a hard-lockup → watchdog reset).

This is inherent to the design (the paint and the waiter share T's live kernel
stack). The "packaged" builds made it **worse** with two avoidable additions
(see §2).

## 1. The mechanism (from the recovered session "blocker waiter")

Direct quotes from `recovered/ses_edcfe2bafffeemezROUjpI2PT7/notes.md`:

- `leak waiter đúng (trong T, perf, (SP & ~0x3fff)|0x3d10)`
- `clobber waiter+0x00/+0x08/+0x10 (NODEPROBE ⇒ VA rác) | paint bị đè trong µs`
- `RB_EMPTY_NODE ⇒ rt_mutex_dequeue bỏ hẳn rb_erase | walk xong 5 ms`
- `select() không dùng được làm hold | stack_fds 256 B trùm waiter ⇒ x24=0`

And from `recovered/ses_edbf99648ffdfG8zCHb7wE0wtJ/notes.md`:

- `waiter treo = SP0-0x1b0 nằm trong frame của mọi syscall “sâu”`
- `setsockopt (không block): waiter->lock trúng … nhưng waiter->tree_entry (+0x00/+0x08) bị đường thoát syscall phá → rb_erase_cached+0x20 panic`

Mechanism:
1. `waiter = SP0-0x1b0` is inside the stack frame of **any deep syscall** on T
   (`setsockopt`, `select`, `nanosleep`, …). So the paint and the waiter alias the
   same memory T will reuse on its next kernel entry/exit.
2. The paint is written by `setsockopt`; **the same syscall's exit**
   (`ret_to_user → work_pending → do_notify_resume` / task_work) rewrites
   `waiter+0x00..0x10`, and an **IRQ at EL0** (T spins in userspace afterward)
   writes a saved `x29/x16` pair over `waiter+0x30/+0x38`.
3. With `SSOPT_EMPTY=1` we set `tree_entry.__rb_parent_color = waiter`
   (`RB_EMPTY_NODE`) so `rt_mutex_dequeue()` (chain `[7]`) returns early and skips
   `rb_erase_cached()`. But if the clobber overwrites that parent_color (or the
   `[11]` pi-tree fields), the walk again reaches `rb_erase_cached()` with garbage
   → panic. Two signatures:
   - `pc: rb_erase_cached+0x20`, `x0=x25=waiter` (tree_entry, `[7]`);
   - hard hang → watchdog reset (last log line `consumer: walk begin`).

## 2. Two aggravators introduced by the "packaging" (B18 → B21 → B25)

### (a) `SSOPT_HOLD` default = 1 → `select()` hold overwrites the waiter
`fops.c:711-717` (current) holds T in `select(64, empty-pipe)` during the walk.
The recovered session proved `core_sys_select` keeps `long stack_fds[32]` (256 B) at
`SP0-0x210..SP0-0x110`, which **covers `waiter`** → it zeroes the paint
(`x24=0`). Code default is `SSOPT_HOLD=1` (`fops.c:661,711`); every known-good run
command passes `SSOPT_HOLD=0`.

### (b) The pre-walk `pr_info + fsync(1)` (patch `_dn_patchB21.py`) widens the window
`main.c` (consumer) currently does:
```c
atomic_fetch_add(&consumer_calls, 1);
pr_info("consumer: walk begin tid=%d\n", tid); fsync(1);   // <-- added by B21
errno = 0;
long sched_ret = sched_setattr_tid(tid, PSELECT_CONSUMER_NICE);   // the walk
```
This logging + `fsync(1)` happens **between** T's paint (`pselect_select_done`) and
the walk `sched_setattr`. While it runs, T is **spinning at EL0** — and the longer
that window, the more likely an IRQ clobbers the paint.

Evidence it is not cosmetic: `ghostlockB18_a64` was built **before** B21 and e2e6
got **14/16** walk successes; the post-B21 builds (`B25`, and our `glA5`) failed at
the walk in the runs we captured. (Also matches the handoff note "B25 chạy tay liên
tiếp thì fail ở walk".)

## 3. What the session concluded about a robust fix

No safe in-kernel hold exists on this machine:
- `select`/`pselect` hold destroys the paint (§2a), and `ppoll`/`do_sys_poll` was
  disassembled and ruled out as a paint vehicle (`PHIEN_2026-10-10.md §9.2`).
- `setsockopt` itself is the paint (non-blocking) and its exit path clobbers the node.

⇒ T must spin at EL0, so the only lever is to **shrink the clobber window** and make
the clobber harmless (`RB_EMPTY_NODE` + waiter leak), which the session did
(14/16). The regression vs B18 is that the window was then widened again.

## 4. Minimal, low-risk changes to try (analysis-based; no functional redesign)

1. `fops.c`: default `SSOPT_HOLD` → **0** (never use the `select()` hold).
2. `main.c`: make the consumer's `pr_info("consumer: walk begin") + fsync(1)`
   **conditional** (e.g. only when `SSOPT_LOG`/`ROUTE_MON`) or drop the `fsync`,
   so it does not sit between the paint and the walk. Keep `walk end` logging.
3. Keep the known-good string: `SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0
   PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SSOPT_HOLD=0`.
4. Re-measure walk success **with a build that lacks (b)** vs the current build,
   redirect-only (`ONLY_FOPS=1 CFI_STOP_VERIFY=1`), to confirm the regression.

> These do not remove the fundamental race (paint on T's live stack); they restore
> the timing the 14/16 build had. A durable fix would need T to stay inside the
> kernel without reusing the waiter's bytes — no such syscall was found on this ROM.

## Confirmed on device (2026-10-10, redirect-only run `glA9`, slide 0x220000)

First end-to-end confirmation of *where* it dies, from the watchdog dump
`dumps/kp_glA9_wedge.gz`:

- Before the reset: `top` showed `%sys` climbing 500% → 704% (≈7/8 CPUs),
  load `84`, many `kworker`/`kworker`+`jbd2` D-state, no Oops.
- The dump contains the RCU stall trace:

```
glA9:13990] INFO: rcu_preempt self-detected stall on CPU
Task dump for CPU 1:
 glA9  R running task  0 13990 11986 0x00000202
 Call trace:
  ...
  gic_handle_irq
  el1_irq
  _raw_spin_unlock_irq+0x20/0x58
  rt_mutex_adjust_prio_chain+0x1dc/0x830
  rt_mutex_adjust_pi+0xa0/0xb8
  __sched_setscheduler+0x890/0xab0
  SyS_sched_setattr+0x2c8/0x358
```

So the **consumer thread is stuck looping inside `rt_mutex_adjust_prio_chain`**
(+0x1dc, on the `_raw_spin_unlock_irq` path = the `[5] retry` loop where
`raw_spin_trylock(&lock->wait_lock)` keeps failing, or the rb-tree walk). This is
the **soft-lockup / livelock** branch of the `PHIEN §9.3` analysis, NOT the
`rb_erase` Oops. It stalls RCU on CPU 1, spreads, and the watchdog reboots the
device (`boot_id` changed, uptime reset). The device recovered on its own.

⇒ **The failing step is FLOW 2.14 (the PI walk)**, and the concrete failure is an
infinite loop in `rt_mutex_adjust_prio_chain`, not a bad write target.
