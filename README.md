# ghostlock-beyond0q — **deep fork** of GhostLock for the Samsung **SM-G970W (beyond0q)** device line

Local-only repository dedicated to the device we are testing: S10e Snapdragon
(`beyond0qltecs`), SD855, Linux **4.14.190**, locked bootloader.

Goal: **temporary (per-boot) userspace root** via a GhostLock port (futex PI UAF) on
a locked, verified-boot Samsung device — no bootloader unlock, no KernelSU
(`MODULE_SIG_FORCE=y`). Ceiling: `RKP_KDP / DMAP_PROT / CFP` ⇒ **data-only** kernel
modifications. Verified method: configfs arbitrary R/W + **`modprobe_path`** root helper.

> NOTE: the commit history in this repo is a **curated reconstruction** built from
> the sessions documented in `docs/`; it is **not** the original development
> history. The upstream source repo (OnePlus line) is `ghostlock-oneplus`; this is a
> **deep fork** scoped to beyond0q (the port diverges substantially from upstream).

## Status (end of session 6)

- **Proven:** fops redirect (mode-4) + **configfs arbitrary R/W**; `physrw` via
  configfs; **root via `modprobe_path`** → a root helper (`call_usermodehelper`, uid 0
  + full caps) that **writes `/data`** and serves a **file-driven command channel**
  (`rcmd`→`rout`). SELinux off, `core_pattern`, `kptr_restrict` writable. cred repoint
  works but trips RKP.
- **Blocked by design:** cred / page-table / `.text` edits (RKP `security_integrity_current`
  panics; `set_memory_rw` is vmalloc-only), unsigned modules (`MODULE_SIG_FORCE`), new
  `/data` files (fscrypt), `/system` (verity), and **persistence across reboot**
  (bootloader unlock infeasible: `oem_unlock_allowed=0`, TEE + AVB/SVB green).
- **Key facts:** `selinux_enforcing=0x2DC8CE8` (≠ `selinux_state`); task_struct **+8**
  (`CONFIG_CC_STACKPROTECTOR` ⇒ `cred=0x858, comm=0x860, pi_blocked_on=0x948`); a real
  `call_usermodehelper` writes `/data` (the "write-crippled" case was the *fake*
  work_struct UMH).
- **User-space permissive (session 7):** the kernel-domain root now *really* flips
  user-space SELinux. The driver marks the `kernel` type in
  `policydb.permissive_map` (a fake `ebitmap_node` in the `core_pattern` buffer) and
  the `mpnl` helper toggles `/sys/fs/selinux/enforce` `1 -> 0` once at start, so the
  kernel emits the real `SETENFORCE(0)` netlink notice and init's cached libselinux
  AVC reloads: `property_service` now accepts `setprop` from `u:r:kernel:s0`
  (`avc ... permissive=1`). KDP is **not** tripped. `settings`/`app_process` stay
  blocked by DEFEX. See `docs/SELINUX_USERSYNC.md`.
- **Root UI (session 8):** `mpnl` is also a **localhost HTTP server** on
  `127.0.0.1:8080` serving an **embedded** single-page app (`src/primitives/webui.html`)
  — drive root commands, `setprop`, and `cmd`-based tweaks from **Chrome on the
  device** (no PC, no APK). Arm with `scripts/arm_root.sh`; verify with
  `scripts/ui_selftest.sh`. See `docs/ROOT_UI.md`.

Full detail: `docs/KSU_ROOT_FINDINGS.md` (sections 1-13 — the main findings, English),
`docs/FLOW_DEBUG.md`, `docs/ROM_MECHANISM_4.14.md`, `docs/RUN_CONFIG.md`,
`docs/DEBUG_WORKFLOW.md`.

## Layout

```
README.md
LICENSE                 # GPL-2.0
docs/                   # English technical docs (findings, flow, run config)
src/                    # exploit source
  core/                 # route + payload builders (single timing-critical process)
  primitives/           # rootshell.c (root shell daemon), mpnl.c + webui.html (root UI)
  payload/              # dnroot.c -> the separate `dnroot` UMH payload binary
  tools/                # glshell.c -> in-process debug shell over the live gadget
  devices/beyond0q/     # this device line (offsets.h)
refs/rom-4.14/          # ROM kernel source subset (reference)
tools/
  build14.sh            # build (WSL) -> *_a64 (driver) + *_dnroot_a64 (payload)
```

## Build & run (WSL)

```
# build -> glXX_a64 (driver) + glXX_dnroot_a64 (UMH payload)
bash tools/build14.sh /tmp/glXX
adb push glXX_a64 /data/local/tmp/glXX
adb push glXX_dnroot_a64 /data/local/tmp/dnroot      # UMH payload (exec'd as uid 0)
adb shell "chmod 755 /data/local/tmp/glXX /data/local/tmp/dnroot"
# KASLR slide
adb shell "cd /data/local/tmp && timeout 60 ./slideprobe > sp.log 2>&1; grep -a -m1 bd4 sp.log"
# redirect phase (safe stop)
adb shell "cd /data/local/tmp && ONLY_FOPS=1 CFI_STOP_VERIFY=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 \
  SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 \
  SLIDE=0x... timeout 120 ./glXX"
```

## Notes

- Raw evidence (kernel dumps, recovered sessions) is kept **locally** and not published
  in this repo.
- Never touch bootloader/partition/flash; avoid `adb uninstall`.

## CLI & log levels (session 5 refactor)

The driver keeps its env flags, and adds a thin CLI:
- `--log=quiet|info|debug` (or `DN_LOG`), default `info`. `debug` enables the
  **timing-sensitive walk logs** (`consumer: walk begin/end` + `fsync`) that are
  otherwise OFF to avoid clobbering the painted waiter during the walk.
- `--stop-after=redirect|verify|umh|cred|full` — maps onto the old env flags:
  `redirect`→`ONLY_FOPS`, `verify`→`ONLY_FOPS`+`CFI_STOP_VERIFY`,
  `umh`→`SKIP_CRED`, `cred`→`SKIP_UMH`, `full`→none.
- Default `SSOPT_HOLD` is now **0** (the `select()` hold overwrites the waiter).

Build from this repo (source of truth): `bash tools/build14.sh /tmp/glXX`.

## Debug shell over the live gadget (`--shell`)

Right after the redirect is verified (and before it is restored), the driver can
drop into a **same-process** shell while the configfs gadget is still installed,
so you can inspect/patch kernel memory from adb **without re-winning the flaky PI
walk**:

```
adb shell "cd /data/local/tmp && GL_SHELL=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 \
  ROUTE_SETSOCKOPT=1 SLIDE=0x... timeout 900 ./glXX --stop-after=verify --shell > gl.log 2>&1 &"
# then, from adb:
adb shell 'echo "peek 0xffffffc0c1234500 8" > /data/local/tmp/gl.cmd'
adb shell 'cat /data/local/tmp/gl.out'          # results
```
Commands: `peek <hexaddr> [n]`, `read <hexaddr> <len>`, `write <hexaddr> <hexbytes>`,
`quit`. Results go to `/data/local/tmp/gl.out`; commands are read from
`/data/local/tmp/gl.cmd` (consumed+deleted). Auto-exits after ~10 min.

## Authorship

Most of this work — exploit analysis, tooling, documentation, and the on-device
investigation — was done by the AI assistant **DeepSeek V4.1 Flash** (DeepSeek),
directed and reviewed by the device owner **jronminh**. See `CREDITS.md`.
