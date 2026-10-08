# ghostlock-beyond0q — GhostLock port for the Samsung **SM-G970W (beyond0q)** device line

Local-only repository dedicated to the device we are testing: S10e Snapdragon
(`beyond0qltecs`), SD855, Linux **4.14.190**, locked bootloader.

Goal: **temporary root** via a GhostLock port (futex PI UAF) — no bootloader
unlock, no KernelSU (`MODULE_SIG_FORCE=y`). Ceiling: `RKP_KDP / DMAP_PROT / CFP`
⇒ **data-only** modifications. Current direction: **(B)** arbitrary R/W through
**configfs** plus UMH (`call_usermodehelper`).

> NOTE: the commit history in this repo is a **curated reconstruction** built from
> the sessions documented in `docs/`; it is **not** the original development
> history. The upstream source repo (OnePlus line) is `ghostlock-oneplus`; this is
> a device-scoped split for beyond0q.

## Status (end of session 5)

- **Proven:** fops redirect (mode-4) + **configfs arbitrary R/W**; `physrw` via
  configfs; UMH exec `retval=0` (≥2 samples, no device reset).
- **Open:** root cause of the **walk stall** (`rb_erase_cached` panic vs
  hard-lockup); **KDP blocking cred** (no evidence yet — `kp_B18b/c` reset
  **silently**); **fscrypt/ENOKEY** (unverified).
- **Critical fixes (session 4):** `selinux_enforcing=0x2DC8CE8` (≠ `selinux_state`);
  task_struct **+8** caused by `CONFIG_CC_STACKPROTECTOR` adding `stack_canary`
  right after `tgid` ⇒ `cred=0x858, comm=0x860, pi_blocked_on=0x948`.

Full detail: `docs/AUDIT_PHIEN5.md`, `docs/BAN_GIAO_PHIEN4.md`,
`docs/PHIEN_2026-10-10.md` (these docs are in Vietnamese, as authored).

## Layout

```
README.md
docs/            # handoff, prompts, session notes, audit (.md)
src/             # exploit source (core + per-device offset table), current tree
  core/
  devices/beyond0q/offsets.h     <-- this device line
tools/
  probes/        # probe_*.c (measure 4.14 layouts: task_struct/cred/mm/kmem/dt/umh)
  build14.sh     # build (WSL) -> *_a64
  analysis/      # kp_scan.py + _dn_*.py/sh (dump reading, measurement, patching)
  scripts/       # other helper scripts (.py/.sh/.ps1/.c/.h)
  refs/          # kallsyms_fixed.txt (image symbol reference)
dumps/           # panic/hang captures (kp*.gz) + index
logs/            # exploit stdout logs (gl*.log, _dn_e2e*.log)
```

## Build & run (WSL)

```
# build -> glXX_a64
bash tools/build14.sh /tmp/glXX
adb push glXX_a64 /data/local/tmp/glXX
adb shell "chmod 755 /data/local/tmp/glXX; cp -f /data/local/tmp/glXX /data/local/tmp/a/e; chmod 755 /data/local/tmp/a/e"
# KASLR slide
adb shell "cd /data/local/tmp && timeout 60 ./slideprobe > sp.log 2>&1; grep -a -m1 bd4 sp.log"
# redirect phase (safe stop)
adb shell "cd /data/local/tmp && ONLY_FOPS=1 CFI_STOP_VERIFY=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 \
  SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 \
  SLIDE=0x... timeout 120 ./glXX"
```

## Notes

- `kp*.gz` are **ZIPs**; the kernel member is `dumpstate_lastkmsg.lst`.
- Identify dumps by **process name** (`ghostlockXX`), **not** filename — labels
  have been wrong before (see `AUDIT_PHIEN5.md §2.1`).
- Never touch bootloader/partition/flash; avoid `adb uninstall`.
