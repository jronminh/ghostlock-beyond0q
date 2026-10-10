# FLOW_DEBUG.md — dry-run of the syscall flow vs ROM source + original exploit

Method: walk `docs/FLOW.md` step by step, cross-check against the ROM kernel source
(`~/ghostlock/src/g9700`) and the **original upstream exploit** (`ghostlock-oneplus`
at `82b2d49`, the last commit before the 4.14 port). No device runs.

## Verdict

**The flow cannot root as it stands, and the break is at FLOW steps 2.12–2.14
(the paint + PI walk).** Failing runs stop at `consumer: walk begin` with no
`walk end` → the walk either panics (`rb_erase_cached` on garbage) or hard-hangs
(watchdog reset). Everything downstream (configfs gadget, UMH, cred) is never
reached in those runs.

## What the original exploit does vs what the port does

Checked with `git show 82b2d49:src/core/fops.c` / `util.c` / `main.c`:

| aspect | ORIGINAL (upstream, pre-port) | PORT (this repo) |
|---|---|---|
| route | **only** `do_pselect_fake_lock_route()` (fd_set painting, T blocks in `select`) | added `do_setsockopt_fake_lock_route()` (stack paint via `setsockopt(...,1000,...)`); `main.c` original calls **only** the pselect route |
| `SSOPT_*` flags | **absent** (grep `setsockopt` in original `fops.c` = 0) | the whole `SSOPT_EMPTY/FAKE_TASK/OWNER0/HOLD/PEEK` family |
| `fake_fops` | `payload_base + FOPS_TABLE_OFF` (page **0x100**) | `payload_base + W0_OFF + 0x18 + 1` (page **0x319**) |
| `fake_task.pi_waiters.rb_leftmost` (mode 4) | `fake_w0 + PI_TREE_ENTRY_OFF` | **0** |
| write value model | `rb_erase` case-1 on `W0->pi_tree_entry` ⇒ `*MISC_FOPS = rb_parent(node) = W0->pi_tree.parent_color = fake_fops` (= table, page 0x100) | observed value = `W0->pi_tree_entry|1` (page 0x319); the port **aligns the table to the observed value** and checks against it |

So the port's route and its write-value model are **port inventions**, diverging from
the upstream. They are *internally consistent* (the redirect is verified against the
observed value — e.g. `cfi fops_before value=…7319 == want=…7319`), but the port's
comments about the writer (**`[7]` vs `[11]`**) contradict each other, and the
`pi_waiters.rb_leftmost` change is what made the written value differ from the
upstream model.

## Why the route is the wrong step (ROM-source cross-check)

The port's route paints the dangling `rt_mutex_waiter` from the **same syscall whose
frame holds it**:

- `waiter = SP0-0x1b0`; `sock_setsockopt` keeps its 0x100-byte buffer at `sp+0x10`
  (frame 0x180) so `buf[0x10..]` overlays `waiter` (geometry from disasm, `PHIEN §3`).
- But `SP0-0x1b0` is inside the frame of **any** deep syscall on T. So after
  `setsockopt` returns, T's next kernel entry/exit (and the syscall's own
  `ret_to_user → do_notify_resume`/task_work) rewrites `waiter+0x00..0x10`
  (`tree_entry`), and an IRQ taken while T spins at EL0 rewrites `waiter+0x30/+0x38`.
- `rt_mutex_adjust_prio_chain` (`kernel/locking/rtmutex.c`) then runs `[7]`
  `rt_mutex_dequeue` → `rb_erase_cached(&waiter->tree_entry, &lock->waiters)` on
  garbage ⇒ `pc: rb_erase_cached+0x20, x0=x25=waiter` (or a hang).

The upstream avoided painting through a syscall that *shares* the waiter's frame:
its pselect route writes the waiter bytes via the `core_sys_select` stack buffer and
keeps T **inside** `do_select`. On this device that geometry fails differently
(`stack_fds` at `SP0-0x210..` also covers `waiter` ⇒ paint lost, `x24=0`;
`PHIEN §9–§11`). So **neither** the original route nor the port's route keeps the
paint intact here — which is why the walk is ~50% flaky.

`SSOPT_EMPTY=1` (RB_EMPTY_NODE on `waiter->tree_entry`) is the port's mitigation: it
makes `[7]` skip the `rb_erase`. But it only works if the painted parent_color
survives; IRQ/nExit clobber the same bytes, so it is probabilistic, not a fix.

## Other port additions (verified, not the crash cause)

- configfs gadget overlay, UMH via fake work_struct — port-only (upstream used pipe
  physrw). Both match the ROM source (`fs/configfs/file.c`, `kernel/umh.c`) and work
  kernel-side (`umh: complete=1 retval=0`).
- UMH child can be uid 0 but cannot write `/data` (`ENOKEY`, no fscrypt keyring) —
  confirmed by the on-device marker `umh_W_fd-1_oe126_ret-555_we0_uid0`.
- cred path resets silently (no Oops) — cause unknown.

## Where it is "wrong" (actionable)

1. **Route/paint (FLOW 2.12–2.14)** is the break. It is a port invention whose paint
   aliases the syscall frame that owns the waiter → unavoidable clobber on this ROM.
2. `fake_fops` / `pi_waiters.rb_leftmost` diverge from upstream; the port works only
   because it aligned the table to an *observed* value. This should be re-derived
   from `rtmutex.c` (which `rb_erase` case fires, what parent is used) and made
   explicit, not fitted to an observation.
3. The `[7]` vs `[11]` comments must be reconciled (see `AUDIT_PHIEN5.md`).

Durable fix direction: use a paint vehicle that does **not** share the waiter's frame
(so T can stay in the kernel with the paint intact). The upstream's `select` vehicle
does not fit this device; `ppoll` was ruled out (`PHIEN §9.2`). Until then the flow
is inherently probabilistic.
