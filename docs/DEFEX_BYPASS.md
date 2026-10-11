# DEFEX on SM-G970W — analysis and bypass

Companion to `docs/KSU_ROOT_FINDINGS.md` §10 and `docs/SELINUX_USERSYNC.md`. DEFEX
("Defeat Exploit") is Samsung's LSM that blocks a **root-credentialed** process from
`exec`'ing files outside a compiled-in **safeplace** allowlist. This document records
what it does on *this* ROM and how the kernel-domain root gets around it.

## Where it lives

Source: `security/samsung/defex_lsm/` (this device's ROM tree); compiled in with
`CONFIG_SECURITY_DEFEX=y`. Sources read locally under `refs/rom-4.14-full/`.

Hooks (`grep task_defex_enforce`): `fs/exec.c` (execve), `fs/open.c` (openat),
`fs/read_write.c` (write), `kernel/sys.c` (setfsuid/setfsgid), plus
`kernel/fork.c`/`exit.c` for credential bookkeeping.

Build flags: `security/defex_lsm/Makefile` adds `-DDEFEX_PERMISSIVE_SP`,
`-DDEFEX_DEBUG_ENABLE`, `-DDEFEX_SYSFS_ENABLE` **only** for
`userdebug`/`eng`/factory builds. This unit is a **`user`** build
(`ro.debuggable=0`, `ro.build.type=user`) ⇒ no `/sys/defex/` and
`global_safeplace_status` is a dead variable (safeplace is a compile-time constant).

## The decision (source)

`core/defex_main.c`:

```c
int task_defex_enforce(struct task_struct *p, struct file *f, int syscall)
{
    if (boot_state_unlocked) return DEFEX_ALLOW;      /* bootloader unlocked */
    if (!p || p->pid == 1 || !p->mm || !is_task_used(p)) return DEFEX_ALLOW;
    ...
    feature_flag = defex_get_features();
    ...
#ifdef DEFEX_SAFEPLACE_ENABLE
    if ((feature_flag & FEATURE_SAFEPLACE) && syscall == __DEFEX_execve) {
        ret = task_defex_safeplace(&dc);
        if (ret == -DEFEX_DENY) { ... kill_process(p); return -DEFEX_DENY; }
    }
#endif
}
```

`task_defex_safeplace()` only applies to **root creds**:

```c
if (!CHECK_ROOT_CREDS(&dc->cred)) goto out;           /* non-root -> allowed */
...
is_violation = rules_lookup(new_file, feature_safeplace_path, dc->target_file);
if (is_violation) { ret = -DEFEX_DENY;
    pr_crit("defex: safeplace violation [task=%s (%s), child=%s, uid=%d]\n", ...); }
```

So: a **root** process may only `execve` a path present in the compiled-in safeplace
list; a non-root process (e.g. `shell`, uid 2000) is not checked.

## Bypass: use the safeplace binaries

`defex_rules.c` packs the safeplace list. It contains, among others:

```
/init  /system/bin/init  /system/bin/sh  /system/bin/toybox  /system/bin/cmd
/system/bin/app_process32  /system/bin/app_process64  /system/bin/dumpsys
/system/bin/logcat  /system/bin/ip  /system/bin/iptables  /system/bin/ss
/sbin/adbd  /vendor/bin/toybox_vendor  /vendor/bin/toolbox  ...
```

Notably `/system/bin/settings` is **absent** — it is only a shell script
(`#!/system/bin/sh` + `cmd settings "$@"`), so DEFEX kills it:
`defex: safeplace violation [task=sh (/system/bin/sh), child=/system/bin/settings, uid=0]`.
But the underlying `/system/bin/cmd` **is** safeplace, so **calling `cmd` directly
works as root**:

```
[verify-only root, uid 0, u:r:kernel:s0]
$ cmd settings get global window_animation_scale      -> 1.0        (rc 0)
$ cmd settings put global window_animation_scale 0.5  -> rc 0, reads back 0.5
$ cmd window density 420                              -> "Override density: 420"
$ cmd package list packages                          -> 411 packages
$ app_process64 ...  / toybox / sh / ip / iptables / dumpsys / logcat  -> OK
```

So the whole "Settings/DPM/debloat" surface is reachable as root through `cmd`
(and `app_process64` for JVM code, `sh` for scripts). See `scripts/root_tweaks.sh`.

## What is still blocked (and why a *global* disable is a RO/RKP problem)

* **Executing a native `/data` ELF as root** via the plain path is denied (its path is
  not safeplace and `CHECK_ROOT_CREDS` is true). But it is trivially bypassed — see
  below.
* **Disabling DEFEX globally** is *not* cleanly possible on this `user` build. DEFEX
  is invoked by **direct calls** (`task_defex_enforce(...)` in `fs/exec.c`,
  `fs/open.c`, `fs/read_write.c`, `kernel/sys.c`), not through the LSM hook list, so
  there is no hook to unlink; and every potential switch is read-only:

  | candidate | why it fails |
  |---|---|
  | `/sys/defex/debug` `sp_status=` | file absent (`DEFEX_DEBUG_ENABLE`/`DEFEX_SYSFS_ENABLE` are userdebug/eng/factory only) |
  | `global_safeplace_status = 0` | dead variable: initial value is `1` in the image ⇒ `DEFEX_PERMISSIVE_SP` **not** defined, so `defex_get_features()` returns the compile-time `GLOBAL_SAFEPLACE_STATUS` and ignores it |
  | `defex_get_features()` / `task_defex_safeplace()` | `.text` (RO) ⇒ RKP/KDP |
  | `boot_state_unlocked = true` | `__ro_after_init` (`R boot_state_unlocked`) ⇒ RO |
  | `security_hook_heads` | `CONFIG_SECURITY_WRITABLE_HOOKS` is off ⇒ `__ro_after_init`; also irrelevant (direct calls) |
  | safeplace rules | `const`/packed at build ⇒ rodata |

  So a global off-switch would need a `.text`/rodata write ⇒ the same RKP wall as
  `cred`. Not attempted.

## Bypass that *is* achievable: bind-mount over a safeplace path

`task_defex_safeplace()` decides on the **mount-namespace path** of the target file
(`core/defex_common.c: get_dc_target_name() -> d_path(&file->f_path, ...)`), then
`rules_lookup(path, feature_safeplace_path, file)`:

* path not in the safeplace list ⇒ `is_violation = !0 = 1` ⇒ **safeplace violation** ⇒
  `-DEFEX_DENY`;
* path in the list ⇒ match ⇒ allow (normal case);
* path in the list **but the file content does not match its recorded hash** ⇒
  `rules_lookup` returns `DEFEX_INTEGRITY_FAIL`, and the handler takes Samsung's
  lenient branch ⇒ `ret = DEFEX_ALLOW`
  (`"Temporary make permissive mode ... system image is changed"`).

A **bind mount** of our own binary over a path that *is* in the safeplace list hits
the third case (path matches, content differs) ⇒ DEFEX allows, and the process runs
as `uid 0` with full caps. No `.text`/rodata/RKP involvement: it is a pure VFS/mount
operation.

Verified on-device (kernel-domain root, SELinux permissive):

```
$ /data/local/tmp/xtest
Killed                                                   # defex: safeplace violation ... child=/data/local/tmp/xtest
$ sh scripts/runroot.sh /data/local/tmp/xtest VIA_BIND
XTEST uid=0 euid=0 gid=0 ctx=u:r:kernel:s0 argc=2 arg1=VIA_BIND   # runs as root
# dmesg: defex: integrity violation [task=sh, child=/system/bin/atrace, uid=0]
```

It runs inside a private mount namespace so the bind mount does not leak into the
system (`scripts/runroot.sh`):

```
runroot.sh /data/local/tmp/<tool> <args...>
  # = unshare -m; mount --bind <tool> /system/bin/<safeplace>; exec /system/bin/<safeplace> <args>
```

## Level achieved

* **Per-boot, per-exec:** DEFEX fully bypassed — arbitrary native code runs as root
  (this is the "like SELinux" level: transient, re-applied each boot by re-running the
  exploit + `mpnl`).
* **Global DEFEX off:** not safely reachable (RO/`.text`).
* **Across reboot:** none (locked bootloader + AVB), same as SELinux.

## Deployment notes

* Run everything through the File-Driven root channel (`rcmd` -> `rout`) as
  `sh -c`, and prefer `cmd <service>` over the wrapper scripts (which are not
  safeplace). `/data` helper binaries should be exec'd **only** as the kernel
  `modprobe_path` helper (kernel-initiated exec, allowed), never by a root
  userspace `execve`.
* `docs/RKP_REFERENCES.md` (Jamf) treats DEFEX as the third wall; this note shows
  that on this ROM the third wall is a *path allowlist* which a root shell can
  walk around by choosing its exec targets.
