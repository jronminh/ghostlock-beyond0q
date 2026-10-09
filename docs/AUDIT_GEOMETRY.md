# AUDIT — pselect geometry on 4.14.190 (SM-G970W), 2026-10-09

> ⟶ **Đọc kèm `PHIEN_2026-10-10.md` §9.** §3/§5 ở đây (task/lock chỉ vào được qua mirror
> `res_in`) vẫn đúng về hình học, và chính điều đó khiến `pselect` **không dùng được**:
> `res_out`/`res_ex` = `SP0-0x1b0..SP0-0x180` = `waiter+0x00..0x2f`, mà `zero_fd_set()` chạy
> trước `do_select()` ⇒ nếu ta *đã* sơn `tree_entry` bằng syscall khác thì `select` sẽ xoá nó.
> Route đúng hiện nay là `setsockopt` (sơn đủ 8 word, không block, spin-park) — xem PHIEN §9.6.

Source of truth for numbers: the device's own `Image` + `kallsyms_fixed.txt`.
All offsets below are `VA - 0xffffff8008000000` (KIMAGE_TEXT_BASE).

## 1. Blocker REWRITE (HANDOFF §10 was a misdiagnosis)

`slide.c` is **dead code** — `slide_leak_kernel_base()`/`slide_child_leak_stext()`
have **no callers** in the tree (verified `grep -rn`). Also `data_addr()` is a
*physical alias* (`P0_DATA_ALIAS_CONST`), independent of KASLR:

```
data_addr(x) = (P0_PAGE_OFFSET | ((x - KIMAGE_TEXT_BASE) + (PHYS_LOAD - PHYS_OFFSET)))
```

So the SLIDE leak cannot be what makes `cfi write` return EINVAL.

The real cause: **the fake waiter fields were written at the wrong word
offsets** because the route's `select()` stack geometry was computed for the
wrong syscall.

## 2. The real stack geometry (disasm Image)

Call chains (both from the same `el0_svc` dispatch SP = S0):

```
futex:        S0 -> sys_futex  (sub sp,#0x70)  -> do_futex
                  do_futex: stp x29,x16,[sp,#-96]!  (sp -= 0x60)
                            sub sp,sp,#0x1b0       (sp -= 0x1b0)   => sp = S0-0x280
                            rt_mutex_init_waiter(x0 = sp+0xd0)      => waiter = S0-0x1b0

pselect6:     S0 -> sys_pselect6 (sub sp,#0xa0) -> core_sys_select
                  core_sys_select: sub sp,sp,#0x1c0  => sp = S0-0x260
                            bits = stack_fds = sp+0x50              => bits   = S0-0x210
```

`shift = (waiter - bits)/8 = (S0-0x1b0 - (S0-0x210))/8 = 0x60/8 = 12`

### Why the port had 8
The port assumed `select()` -> `sys_select` (frame `0x80`) giving
`bits = S0-0x1f0`, shift 8. **But glibc `select()` issues `pselect6`**
(`__NR_pselect6=72`), not `__NR_select`:

* static binary: `__select` does `mov x6,#0x48` (72) then `__syscall_cancel`
* this kernel: `sys_call_table[1067]` -> `sys_select` is **ENOSYS** at runtime
  (probe: `pselect returned ret=-1 errno=38`)
* `sys_pselect6` frame = `0xa0`, `sys_select` frame = `0x80`

## 3. Consequence of shift=12

`waiter word k` sits at global word `12+k`:

| waiter field | word | global | backing store |
|---|---|---|---|
| tree.parent_color | 0 | 12 | ex[2] |
| tree.right | 1 | 13 | ex[3] |
| tree.left | 2 | 14 | ex[4] |
| pi_tree.parent_color | 3 | 15 | res_in[0] |
| pi_tree.right | 4 | 16 | res_in[1] |
| pi_tree.left | 5 | 17 | res_in[2] |
| **task** | 6 | 18 | **res_in[3]** |
| **lock** | 7 | 19 | **res_in[4]** |
| prio | 8 | 20 | res_out[0] |
| deadline | 9 | 21 | res_out[1] |

`in/out/ex` only cover global 0..14, so **task/lock fall in `res_in`**.
`do_select()` computes `res_in_word[k] = in_word[k] & ready_mask`, so they are
still attacker-controllable — but only *while selected fds are ready*, and the
write-back happens at the end of the `do_select` poll loop.

## 4. Fix applied
`fops.c::pselect_put_global_word` now maps the `res_*` sets back onto
`in/out/ex` (`res_in word k <- in word k`, etc.), the shift=8-only
`in[0..2]` hack is removed, and `PSELECT_WAITER_WORD_SHIFT` is 12.
`slide.c` gets the same generalized placement, a compact 4.14 `words[]`,
and the timerfd arm. `run_exploit()` now calls `slide_leak_kernel_base()`
before the fops redirect so `text_addr()` is correct (RANDOMIZE_BASE=y).

## 5. Observed behaviour after the fix
* shift 12 run (`ghostlock15`): device **reboots** during the mode-4 route
  (previously it silently did nothing -> EINVAL). The PI walk now engages.
* Remaining risk (upstream feasibility rule): for a compact waiter the lock
  field must be at waiter word <= 7 (word+7 <= 14). 4.14 is word 12, i.e.
  beyond the purely user-controlled window; the `res_in` mirror is the only
  way in, and it is inherently racy (res_in is filled at select-return).
