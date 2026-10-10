# ROM_MECHANISM_4.14.md — port vs the target ROM (4.14) source

The original upstream targets **kernel 6.x**; this deep fork targets the **4.14**
ROM. So the port must be checked against the **target ROM source**, not the
upstream. A reference copy is now in `refs/rom-4.14/` (from the OSRC
`SM-G9700/G970W` 4.14 source; also extracted in WSL at `~/ghostlock/src/g9700`,
and shipped as `E:\Library\Desktop\SM-G9700.zip`).

## Struct/mechanism matches (port assumption ⇄ ROM 4.14 source)

| Port assumption | ROM 4.14 source | Verdict |
|---|---|---|
| `struct rt_mutex`: `wait_lock@0, waiters@0x08 (rb_root 8 + rb_leftmost 8), owner@0x18` | `refs/rom-4.14/include/linux/rtmutex.h` (`raw_spinlock_t wait_lock; struct rb_root_cached waiters; struct task_struct *owner;`) | ✅ |
| `struct rt_mutex_waiter` compact: `tree@0, pi_tree@0x18, task@0x30, lock@0x38, prio@0x40, deadline@0x48` | `refs/rom-4.14/kernel/locking/rtmutex.c` `struct rt_mutex_waiter { rb_node tree_entry; rb_node pi_tree_entry; task_struct *task; rt_mutex *lock; int prio; u64 deadline; }` | ✅ (`offsets.h: waiter_compact=1, waiter_pi_tree_off=0x18`) |
| `struct configfs_buffer`: `needs_read_fill@0x48, bin_buffer@0x50, bin_buffer_size@0x58, cb_max_size@0x5c` | `refs/rom-4.14/fs/configfs/file.c` + `include/linux/mutex.h` (+`CONFIG_KPERFMON` adds `unsigned long time` ⇒ `sizeof(mutex)=0x28`) | ✅ |
| UMH: `umh_complete` completes (no `kfree`) when `complete != NULL` | `refs/rom-4.14/kernel/umh.c` `xchg(&sub_info->complete, NULL)` → `complete(comp)` | ✅ |
| task tail **+8** (`stack_canary` after `tgid`) | `refs/rom-4.14/include/linux/sched.h` `#ifdef CONFIG_CC_STACKPROTECTOR unsigned long stack_canary;` | ✅ |
| `selinux_enforcing` (not `selinux_state`) | `refs/rom-4.14/security/selinux/include/security.h` `enforcing_enabled()` returns global `selinux_enforcing` | ✅ |

So the port's **struct layout and side mechanisms match the 4.14 ROM**.

## The write value is NOT a constant — the key mechanism point

ROM 4.14 `refs/rom-4.14/…` → `include/linux/rbtree_augmented.h`
`__rb_erase_augmented()` case 1:

```c
pc = node->__rb_parent_color;
parent = __rb_parent(pc);
__rb_change_child(node, child, parent, root);
if (child) {
    child->__rb_parent_color = pc;   /* <-- written value == node's parent_color */
    ...
}
```

i.e. erasing a node writes **`node->__rb_parent_color`** into `child`, where
`child = node->rb_right`. For the mode-4 redirect (`child = *MISC_FOPS`), the value
written is **whatever the erased node's parent_color holds**.

- **Upstream** set it explicitly: `write_pc = fake_fops` and
  `fake_fops = payload_base + FOPS_TABLE_OFF` (page 0x100) ⇒ the erased node's
  parent_color == the fake fops table address. Self-consistent.
- **Port** sets `write_pc = payload_base + FOPS_TABLE_OFF` (page 0x100) **but**
  `fake_fops = payload_base + W0_OFF + 0x18 + 1` (page 0x319). These differ, and the
  port verifies `*MISC_FOPS == fake_fops` (page 0x319). The observed value
  (`…7319`, e.g. `gl_QA_peek.log`) matches **page 0x319**, not `write_pc` (0x100) —
  so the erased node is **not** `W0->pi_tree_entry`; the actual erased node's
  parent_color is `&W0->pi_tree_entry|1` (page 0x319), i.e. the **waiter's**
  `pi_tree_entry` after `rt_mutex_enqueue_pi()` reparented it to `W0->pi_tree_entry`.

**Consequence:** the port's `fake_fops`/`pi_waiters.rb_leftmost` were fitted to an
*observed* write value rather than derived from the ROM's `rb_erase` semantics.
That is fragile and the code comments contradict each other (`[7]` vs `[11]`, see
`AUDIT_PHIEN5.md`). It works today (the check passes), but it is not the upstream
mechanism.

## Conclusion

- **No struct/offset mismatch with the 4.14 ROM** was found — the port's layout
  matches (`refs/rom-4.14/`).
- The one mechanism-level divergence is the **mode-4 write identity**
  (`write_pc` vs `fake_fops` vs `pi_waiters.rb_leftmost`), fitted to observation
  instead of derived from `rb_erase` semantics. Recommend re-deriving it explicitly
  (set the erased node's parent_color = `fake_fops`) so the write target and value
  are by construction, not by luck.
- This does not change the crash cause: the **paint clobber** in the route
  (`FLOW_DEBUG.md §2.12–2.14`) is what stops root.
