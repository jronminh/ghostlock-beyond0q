# ghostlock-beyond0q — per-boot root on the Samsung SM-G970W (locked, verified boot)

A working port of the **GhostLock** futex-PI exploit to the Samsung Galaxy S10e
(**SM-G970W**): a **per-boot, userspace uid-0 root** on a device with a **locked
bootloader and AVB/SVB green** — no unlock, no flash, no KernelSU
(`MODULE_SIG_FORCE=y`), no persistence. The chain wins a futex priority-inheritance
use-after-free, redirects `/dev/ashmem` fops through configfs for **arbitrary kernel
read/write**, and lands on `modprobe_path` to run a root helper that also serves an
**on-device control UI**.

## Target (exact)

| | |
|---|---|
| Model / market code | **SM-G970W** (Galaxy S10e, Snapdragon 855) |
| Device / board code | **`beyond0q`** (`ro.product.device`) |
| Product name | `beyond0qltecs` |
| Android | 12 (SDK 31) |
| ROM build code | **`G970WVLU9IXE1`** — display id `SP1A.210812.016.G970WVLU9IXE1` |
| Fingerprint | `samsung/beyond0qltecs/beyond0q:12/SP1A.210812.016/G970WVLU9IXE1:user/release-keys` |
| Kernel | **`4.14.190-23725627-abG970WVLU9IXE1`** |
| Security patch | 2023-03-01 |
| Build type | `user` (`ro.debuggable=0`) |
| CSC / region | `XAC` (`ro.csc.sales_code`) |
| Baseband / bootloader | `G970WVLU9IXE1` |
| Boot state | `ro.boot.verifiedbootstate=green`, `ro.boot.flash.locked=1`, `sys.oem_unlock_allowed=0` |
| Knox | `ro.config.knox=v30` |
| Chipset | Qualcomm SD855, with TrustZone RKP |

Confirm you have the right unit before anything else:

```
adb shell 'getprop ro.product.device ro.build.display.id ro.build.version.security_patch; uname -r'
# expect:  beyond0q
#          SP1A.210812.016.G970WVLU9IXE1
#          2023-03-01
#          4.14.190-23725627-abG970WVLU9IXE1
```

The exploit's symbol/struct offsets are pinned to **this exact build**; any other
firmware requires re-deriving them (`REPRODUCE.md` §2).

## What we achieved

- **Exploit primitives work:** the futex PI UAF is reproducibly reachable; the
  `/dev/ashmem` fops redirect installs **configfs arbitrary kernel R/W**.
- **Root:** `modprobe_path` runs our helper as **uid 0, full caps**
  (`u:r:kernel:s0`) via `call_usermodehelper` — a real root process that can
  read/write `/data`.
- **Real user-space permissive SELinux:** marking the `kernel` type in the loaded
  `policydb.permissive_map` makes `setprop` from that domain actually pass
  (`avc ... permissive=1`), without tripping RKP.
- **DEFEX bypass:** any `/data` ELF runs as root by bind-mounting it over a
  compiled-in *safeplace* path.
- **On-device control UI:** the helper is a **localhost HTTP server**
  (`127.0.0.1:8080`) serving an **embedded** single-page app — drive root commands,
  `setprop`, and `cmd`-based tweaks from **Chrome on the phone** (no PC, no APK).
- **Reachable surface:** SELinux off, `modprobe_path`/`core_pattern`/`kptr_restrict`
  writes, `setprop` + persistent properties, `cmd settings`/`cmd package` tweaks.

## What is blocked — by design

| wall | why |
|---|---|
| `cred` / page-table / `.text` / `.rodata` writes | RKP (`security_integrity_current` panic); KDP protects the kernel image |
| unsigned modules | `CONFIG_MODULE_SIG_FORCE=y` |
| `/system` writes | dm-verity |
| creating **new** `/data` files from the kernel domain | fscrypt (helper carries init's keyring) |
| **persistence across reboot** | locked bootloader + TEE + AVB/SVB `green`; unlock infeasible |

⇒ the result is a **transient, per-boot** root. Everything re-arms on each boot.

## Quick start

Full from-source walkthrough: **[`REPRODUCE.md`](REPRODUCE.md)**. Short version:

```
# 1. build every artifact -> <base>_a64 (+ <base>_pwn2)
bash tools/build14.sh /tmp/glXX
#    driver        = glXX_a64
#    daemon + UI   = glXX_mpnl_a64      (push to /data/local/tmp/mpnl)
#    UMH payload   = glXX_dnroot_a64
#    slide probe   = glXX_slideprobe_a64
#    trigger file  = glXX_pwn2

# 2. arm per boot (slide probe -> driver -> trigger -> verify)
ADB=adb DRIVER=/data/local/tmp/glXX MPNL=/data/local/tmp/mpnl \
  bash scripts/arm_root.sh
```

Then open `http://127.0.0.1:8080/` in Chrome **on the device**. The precise,
one-command-per-step procedure and the working flag set are in
`docs/DEBUG_WORKFLOW.md` and `docs/RUN_CONFIG.md`.

## Layout

```
README.md
REPRODUCE.md            # build + run from source (start here)
TODO.md                 # planned work (e.g. upstream profile contribution)
LICENSE                 # GPL-2.0
docs/                   # findings, flow, run config, root UI
src/                    # exploit source
  core/                 # route + payload builders (single timing-critical process)
  primitives/           # rootshell.c, mphelper.c, mpnl.c + webui.html (root daemon + UI)
  payload/              # dnroot.c -> the `dnroot` UMH payload binary
  tools/                # glshell.c (debug shell), slideprobe.c, trigger.c, getid.c, rsd.c
  devices/beyond0q/     # this device line (offsets.h)
refs/rom-4.14/          # ROM kernel source subset (reference)
scripts/                # host/device helpers (arm_root.sh, ui_selftest.sh, runroot.sh, ...)
tools/
  build14.sh            # build ALL artifacts (WSL/arm64 host) -> *_a64 + *_pwn2
```

## Docs

- `REPRODUCE.md` — build and run from source, offsets/KASLR, troubleshooting.
- `TODO.md` — planned work, including an upstream SM-G970W profile for Root My Galaxy.
- `docs/KSU_ROOT_FINDINGS.md` — the findings (primitives, symbols, root channel).
- `docs/SELINUX_USERSYNC.md` — why `setprop` needs a policy patch, not just a raw write.
- `docs/DEFEX_BYPASS.md` — the safeplace bind-mount bypass.
- `docs/ROOT_UI.md` — the localhost control panel (design, API, security model).
- `docs/RKP_*.md`, `docs/KGSL_CVE_2023_21665.md` — protection stack and the GPU path.
- `docs/DEBUG_WORKFLOW.md`, `docs/RUN_CONFIG.md` — the device loop and working flags.

## Related work

This is a port of **GhostLock (CVE-2026-43499)**, a ~15-year-old rtmutex/futex
use-after-free disclosed in 2026. It is not the discovery.

- **Upstream:** [`JoinChang/ghostlock-oneplus`](https://github.com/JoinChang/ghostlock-oneplus).
- **References:** Nebu, *IonStack part II: GhostLock*; [NVD CVE-2026-43499](https://nvd.nist.gov/vuln/detail/CVE-2026-43499); advisories (Red Hat, SUSE, AWS, AlmaLinux, CloudLinux).
- **Other ports (examples):** [`YuKongA/ghostlock-app`](https://github.com/YuKongA/ghostlock-app); [`yijiacloud/GhostLock-OPPO-PCKM00`](https://github.com/yijiacloud/GhostLock-OPPO-PCKM00); [`xiaohj233/ghostlock-x200-root`](https://github.com/xiaohj233/ghostlock-x200-root); [`ccp-p/ghostlock-cve-2026-43499-4.19-k40`](https://github.com/ccp-p/ghostlock-cve-2026-43499-4.19-k40); [`alex193a/Root-My-Pixel`](https://github.com/alex193a/Root-My-Pixel); [`wxxsfxyzm/GhostLock-Galaxy`](https://github.com/wxxsfxyzm/GhostLock-Galaxy); [`snothin/GhostSam`](https://github.com/snothin/GhostSam); [`mobilehackinglab/ghostlock-a17`](https://github.com/mobilehackinglab/ghostlock-a17); [`veygax/HORiZonstack`](https://github.com/veygax/HORiZonstack); [`R0rt1z2/GhostLock`](https://github.com/R0rt1z2/GhostLock).
- **Tooling:** [`ctn-Qvo/auto_extract_offsets`](https://github.com/ctn-Qvo/auto_extract_offsets); [`CakesTwix/Android-CVE-2026-43499`](https://github.com/CakesTwix/Android-CVE-2026-43499); [`PeronGH/ghostlock-selinux-disabler`](https://github.com/PeronGH/ghostlock-selinux-disabler).
- **This device:** no other public port of `beyond0q` / SM-G970W was found. Specific
  to this port: msm-4.14 / SD855, the RKP/KDP data-only ceiling, the DEFEX and fscrypt
  workarounds, the on-device UI, and a from-source build (`REPRODUCE.md`).

## CLI & log levels

The driver keeps its env flags and adds a thin CLI:
- `--log=quiet|info|debug` (or `DN_LOG`), default `info`. `debug` enables the
  **timing-sensitive walk logs** (`consumer: walk begin/end` + `fsync`) that are
  otherwise OFF to avoid clobbering the painted waiter during the walk.
- `--stop-after=redirect|verify|umh|cred|full` — maps onto the env flags:
  `redirect`→`ONLY_FOPS`, `verify`→`ONLY_FOPS`+`CFI_STOP_VERIFY`,
  `umh`→`SKIP_CRED`, `cred`→`SKIP_UMH`, `full`→none.
- Default `SSOPT_HOLD` is **0** (the `select()` hold overwrites the waiter).

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

## Notes

- Raw evidence (kernel dumps, logs) is kept outside this repo.
- **Never** touch the bootloader, partitions, or flash; avoid `adb uninstall`.
- See `CREDITS.md` for authorship.
