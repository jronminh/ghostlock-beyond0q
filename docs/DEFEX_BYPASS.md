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

## What is still blocked (and why full disable is a RO/RKP problem)

* **Executing a native `/data` ELF as root** is denied (its path is not safeplace and
  `CHECK_ROOT_CREDS` is true). A non-root (shell) exec is allowed but has no root.
  Workarounds: run code via `app_process64` (JVM, from a `/data` DEX — DEFEX only
  checks `execve`, not subsequent `dlopen`/DEX loading), via `sh`, or via `cmd`.
* **Disabling DEFEX globally** would require either
  * `boot_state_unlocked = true` — but it is `__ro_after_init` (`R boot_state_unlocked`
    in kallsyms) ⇒ a read-only page; writing it trips STRICT_KERNEL_RWX/RKP, or
  * patching `defex_get_features()` / `task_defex_enforce()` / the packed rules — all
    in `.text`/rodata ⇒ RKP/KDP territory,
  * the `/sys/defex/debug` `sp_status=` toggle — **not present on a `user` build**.
  None attempted; the safeplace-binary route already covers the useful cases.

## Deployment notes

* Run everything through the File-Driven root channel (`rcmd` -> `rout`) as
  `sh -c`, and prefer `cmd <service>` over the wrapper scripts (which are not
  safeplace). `/data` helper binaries should be exec'd **only** as the kernel
  `modprobe_path` helper (kernel-initiated exec, allowed), never by a root
  userspace `execve`.
* `docs/RKP_REFERENCES.md` (Jamf) treats DEFEX as the third wall; this note shows
  that on this ROM the third wall is a *path allowlist* which a root shell can
  walk around by choosing its exec targets.
