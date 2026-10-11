# SELinux user-space sync — why `setprop` fails on the kernel-domain root

Companion to `docs/KSU_ROOT_FINDINGS.md` (§14) — this document explains **exactly why**
the kernel-domain root (`u:r:kernel:s0`, `uid 0`) cannot set properties even with
`selinux_enforcing=0`, and what it would take to fix it. All facts below were
confirmed against this device's ROM source (`refs/rom-4.14-full/`) and/or on-device.

## TL;DR

* Writing the raw `selinux_enforcing` variable to 0 makes the **kernel** permissive
  (`getenforce` → `Permissive`, `/sys/fs/selinux/enforce` → `0`, `avc_denied()`
  returns 0). **This is not enough.**
* Android's `property_service` (in `init`) checks `property_service set` in
  **user space** via `libselinux`, which caches `avc->enforcing` at first use.
  A raw kernel variable write is invisible to that cache.
* `libselinux` only refreshes the cache from (a) the kernel's netlink
  `SELNL_MSG_SETENFORCE` broadcast, or (b) the mmap status page — and both are
  emitted **only** by `sel_write_enforce()` (`/sys/fs/selinux/enforce`).
* Forging the netlink message from user space is **blocked**: `libselinux` rejects
  packets whose source portid is not 0 (kernel):
  `avc: warning: received spoofed netlink packet from: <pid>`.
* `echo 1 > /sys/fs/selinux/enforce` *succeeds* (once the raw var is 0 the
  `security:setenforce` check is permissive) and *does* sync user space to
  enforcing=1 — but the reverse (1→0) is denied by policy.
* The fix: make the `kernel` domain itself **permissive in the policy**
  (`policydb.permissive_map`). Then `security_compute_av[_user]()` sets
  `AVD_FLAGS_PERMISSIVE` for it and both the kernel and `libselinux` allow the
  operation regardless of the cached enforcing flag. **Implemented and verified
  on-device — see §6b.**

## 1. The two enforcement paths (source)

`security/selinux/include/security.h` (4.14, `CONFIG_SECURITY_SELINUX_DEVELOP=y`):

```c
extern int selinux_enforcing;
static inline bool enforcing_enabled(struct selinux_state *state) { return selinux_enforcing; }
static inline void enforcing_set(struct selinux_state *state, bool value) { selinux_enforcing = value; }
```

`security/selinux/avc.c`, `avc_denied()`:

```c
#ifdef CONFIG_ALWAYS_ENFORCE
    if (!(avd->flags & AVD_FLAGS_PERMISSIVE)) return -EACCES;
#else
    if (selinux_enforcing && !(avd->flags & AVD_FLAGS_PERMISSIVE)) return -EACCES;
#endif
```

The device config has **no `CONFIG_ALWAYS_ENFORCE`**, so the effective knob is the
plain `int selinux_enforcing` — which our exploit writes to 0 (no RKP panic; it is
not `__kdp_ro`). Only `selinux_enforcing_boot`, `selinux_enabled` and
`init_sec`/`task_security_struct` are `__kdp_ro` (`hooks.c` lines ~123/210/240).

So per the *kernel* the policy is permissive after the write. The problem is on the
user side.

## 2. The status page is never updated by a raw write

`selinuxfs.c`, `sel_write_enforce()` only touches the status page / notifier when
the value actually changes:

```c
old_value = enforcing_enabled(state);
if (new_value != selinux_enforcing) {          // raw write already made it 0 -> skip!
    ... avc_has_perm(..., SECURITY__SETENFORCE) ...
    enforcing_set(state, new_value);
    selnl_notify_setenforce(new_value);            // netlink broadcast (group AVC)
    selinux_status_update_setenforce(state, new_value); // status page + sequence
}
```

On-device `/sys/fs/selinux/status` after the raw write:

```
version=1  sequence=0  enforcing=1  policyload=0  deny_unknown=1
```

`sequence=0` proves `selinux_status_update_*` was never called for this boot. The
raw write therefore leaves `enforcing=1` in the status page — the value
`libselinux` sees.

## 3. libselinux caches enforcing and only trusts the kernel over netlink

Device `/system/lib64/libselinux.so` (Android 12), disassembly highlights:

* `selinux_check_access()` calls `avc_netlink_check_nb()` before every check
  (`bl` at `0xf47c`), i.e. it drains the SELinux netlink socket on each call.
* `avc_netlink_process()` handles `SELNL_MSG_SETENFORCE` and updates the AVC.
* `selinux_status_updated()` exists but has **no internal callers** — the status
  page is not consulted by the property path.
* `avc_netlink_open()` binds to multicast group **1** (`SELNL_GRP_AVC`).
* On a packet from user space it logs
  `%s: received spoofed netlink packet from: %u` and drops it.

Confirmed on-device by running a user-space netlink forge from the root helper:

```
mp_ran: nl setenforce0 rc=-111          # sendto -> ECONNREFUSED (unicast to kernel cb)
dmesg : avc: warning: received spoofed netlink packet from: 10396
        avc: denied { set } for property=... scontext=u:r:kernel:s0
             tcontext=u:object_r:telephony_config_prop:s0 tclass=property_service permissive=0
```

`permissive=0` is the user-space AVC's view (kernel permissive, user space not).

## 4. `sel_write_enforce` can move 0→1 but not 1→0

Verified on-device (kernel at raw `selinux_enforcing=0`):

```
echo 1 > /sys/fs/selinux/enforce   -> rc=0   (check permissive because var==0)
                                      + syncs user space to enforcing=1
echo 0 > /sys/fs/selinux/enforce   -> rc=1   (check now enforcing; kernel domain denied)
```

After the `echo 1`, even `/system` binaries could no longer be `exec`'d from the
kernel domain ("inaccessible or not found") — the `kernel` domain is heavily
restricted under enforcing.

The policy confirms no domain may `setenforce` (`plat_sepolicy.cil`):

```
(neverallow base_typeattr_188 kernel (security (setenforce)))
(dontaudit kernel self (security (setenforce)))
# no (allow ... (security (setenforce))) anywhere
```

## 5. The fix: permissive policy for the `kernel` domain

`security/selinux/ss/services.c` (both `security_compute_av` and
`security_compute_av_user`):

```c
/* permissive domain? */
if (ebitmap_get_bit(&policydb->permissive_map, scontext->type))
    avd->flags |= AVD_FLAGS_PERMISSIVE;
```

If the `kernel` type is in `permissive_map`, then:
* the kernel's `avc_denied()` returns 0 (the `echo 0 > enforce` check passes, the
  kernel emits the real `SETENFORCE(0)` notice, and user space finally syncs), and
* `security_compute_av_user()` returns `AVD_FLAGS_PERMISSIVE`, so `libselinux`
  allows the property check immediately — no user-space cache change needed.

Relevant structures (from the ROM source):
* `security/selinux/ss/services.h`: `struct selinux_ss { struct sidtab *sidtab;
  struct policydb policydb; rwlock_t policy_rwlock; ... struct page *status_page; ... }`
  and `static struct selinux_ss selinux_ss;` (`ss/services.c`) — a static global.
* `security/selinux/ss/policydb.h`: `struct policydb { ... struct ebitmap
  policycaps; struct ebitmap permissive_map; ... }`.
* `security/selinux/ss/ebitmap.h`: `struct ebitmap { struct ebitmap_node *node;
  u32 highbit; }`, `struct ebitmap_node { struct ebitmap_node *next;
  unsigned long maps[6]; u32 startbit; }` (`EBITMAP_SIZE = 384` bits/node).

Base (no-slide) symbols from `kallsyms_fixed.txt`:
```
selinux_state     0xffffff800adc8cc8
selinux_enforcing 0xffffff800adc8ce8
selinux_ss        0xffffff800adcc178
init_cred         0xffffff800a20e0d0
init_sec          0xffffff800a20e1e0   (task_security_struct, __kdp_ro)
```

### Option A — patch the in-memory `policydb.permissive_map` (preferred)

Set `permissive_map` so `ebitmap_get_bit(type_of_kernel)` returns 1. Since the map
is empty (`node=NULL, highbit=0`) a fake `struct ebitmap_node` must be supplied;
its `maps[]` all-ones and `startbit` chosen to cover the kernel type, with
`highbit` above it. The fake node can live in an unused writable kernel buffer
(e.g. `core_pattern`, 128 B). Requires `offsetof(struct policydb, permissive_map)`
(no DWARF in `vmlinux.elf`, but computable by compiling offsets against the ROM
source the same way `hello.ko` was built) and the kernel type value (from
`sidtab.isids[SECINITSID_KERNEL-1].leaf.context.type`).

### Option B — reload a modified policy

Pull `/sys/fs/selinux/policy` (world-readable), add the `kernel` type to the
serialized `permissive_map` ebitmap, and write it back to `/sys/fs/selinux/load`
from a root process. `sel_write_load()`'s `security:load_policy` check passes while
the raw `selinux_enforcing=0` (permissive). Risk: `security_load_policy` rewrites
the policydb — RKP `ss_initialized` handling must be validated on-device.

## 6. Deployment constrains

* Every variant still depends on the per-boot exploit (kernel R/W). There is no
  persistence (locked BL + AVB green + RKP).
* `DEFEX` still blocks `uid 0` from `exec`'ing `/data` binaries, and `fscrypt`
  still blocks *creating new* `/data` files from the kernel domain — so the "fix"
  is delivered either as an in-exploit hook or via the `modprobe_path` helper's
  file channel, not as a new `/data` binary exec'd by root.

## 6b. IMPLEMENTED — verified working

The in-memory patch (Option A) is now wired into the exploit and verified
on-device:

* `src/core/target.h`: `SELINUX_SS_OFF 0x02DCC178` (the static `selinux_ss`),
  `SELINUX_PMAP_OFF 0x01C8` (= `offsetof(struct selinux_ss, policydb)` 8 +
  `offsetof(struct policydb, permissive_map)` 0x1C0), `SELINUX_TYPE_KERNEL 791`,
  `SELINUX_EBITMAP_SIZE 384`.
* `src/core/fops.c` (`MP_PATH` hook): writes a fake `ebitmap_node`
  (`next=0, maps[6]=~0, startbit=768`) into the unused `core_pattern` buffer and
  points `permissive_map.node`/`.highbit` at it.
* `src/primitives/mpnl.c` (built by `tools/build14.sh` -> `<name>_mpnl_a64`):
  the root helper toggles `/sys/fs/selinux/enforce` `1 -> 0` once at daemon
  start.

On the device (verify-only run — no long `--shell` window):

```
[hook] permissive_map @...54340 node=...6e120 startbit=768 highbit=1152 wr=60 rb_node=... rb_highbit=1152
[mp_ran] selinux sync done; enforce now=0
[rout]  getenforce=Permissive
        setprop debug.gtest.probe2 hello -> rc=0, value "hello"
        setprop persist.dbg.volte_avail_ovr 1 -> rc=0, value 1
[dmesg] avc: denied { set } for property=... scontext=u:r:kernel:s0 ... permissive=1
```

`permissive=1` (was `permissive=0`) confirms real user-space permissive mode, and
`property_service` now accepts `setprop` from the kernel domain.

**`settings` is still blocked** — but by DEFEX, not SELinux:
`defex: safeplace violation [task=sh (/system/bin/sh), child=/system/bin/settings, uid=0]`.
So framework tweaks that go through `settings`/`app_process` need the
data-layer path instead; `setprop` (and the persisted-property file) work.

**KDP/RKP are NOT tripped by the `permissive_map` write.** `kdp_init()` only
hands RKP: `ss_initialized`, `selinux_enforcing_boot`, `selinux_enabled`,
`init_sec` (`__kdp_ro`); `permissive_map` is not in the protected set. No
`RKP ... VIOLATION` / `security_integrity` panic occurred. (A reboot seen while
developing was an **exploit** artifact: the long-lived `glA21 --shell` gadget
left the `/dev/ashmem` fops redirect installed for ~10 min, and another process's
`read()` landed in `configfs_read_file` -> `mutex_lock` oops. The shipped flow
uses `--stop-after=verify`, which restores the fops immediately.)

## 7. Evidence log

| Step | Observation |
|---|---|
| raw `selinux_enforcing=0` | `getenforce`=Permissive, `/enforce`=0, status page `enforcing=1 sequence=0` |
| `setprop` from kernel domain | fails; `permissive=0` avc |
| netlink `SETENFORCE(0)` forge from root | `rc=-111`; `avc: warning: received spoofed netlink packet from: <pid>` |
| `echo 1 > /sys/fs/selinux/enforce` | rc=0, syncs user space to 1, then `/system` exec denied |
| `echo 0 > /sys/fs/selinux/enforce` | rc=1 (policy denies `kernel` domain) |
| policy CIL | no `setenforce` allow; only `neverallow`/`dontaudit` for `kernel` |
