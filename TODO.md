# TODO

## Contribute an SM-G970W profile to Root My Galaxy

Objective: add this device (`SM-G970W` / `beyond0q`) to the community Root My
Galaxy effort, following the layout of
[`BuSung-dev/Root-My-Galaxy-Payloads`](https://github.com/BuSung-dev/Root-My-Galaxy-Payloads)
and its `docs/PORTING.md`.

Reference material to mirror:

- `docs/PORTING.md` — firmware identity, `boot.img.lz4` extraction,
  `vmlinux-to-elf`, `llvm-nm`, BTF recovery, offset derivation.
- `kernelsu/README.md` — versioned KernelSU late-load artifacts and the
  Samsung KDP/RKP/DEFEX patch.
- `support/targets-v3.json` — the schema-v3 support feed.
- `artifacts/<profile>/` and `docs/SM-<model>-<build>.md` — the per-device
  payload and validation record.

Tasks:

1. **Firmware identity.** Fetch the exact build with `samloader-rs` (FUS);
   record AP/CSC/CP, `ro.build.fingerprint`, `ro.build.display.id`, kernel
   release, and confirm against this repo's Target table.
2. **Kernel artifacts.** Extract the kernel `Image` from `boot.img.lz4`;
   recover a symbolized ELF (`vmlinux-to-elf`) and symbols (`llvm-nm`); extract
   BTF if present. Record SHA-256 for the boot image and kernel.
3. **Profile.** Create the target profile (their `target.h` style) with every
   symbol and `struct` offset verified against the recovered image; include the
   **legacy 4.14 `rt_mutex_waiter` layout** (their closest record is the 5.10
   A15 note, not 4.14).
4. **App-domain path.** Evaluate their KASLR route (`tracefs` discovery plus the
   physical-P0 oracle) to remove this port's `perf_event` dependency, so the
   payload can run from `untrusted_app` with no adb step.
5. **KernelSU late-load.** Assess `ksud late-load` (kallsyms-aware manual
   loader, `CONFIG_KSU_SAMSUNG_NO_PATCH_TEXT=y`, the
   `samsung-kdp-rkp-defex` patch) against 4.14 + `MODULE_SIG_FORCE=y`; if
   viable, produce a `kernelsu/` artifact for this KMI.
6. **Payload build.** Produce `cve-2026-43499-app.so` (and `cve-2026-43499-root`
   where applicable) with their `Makefile` target.
7. **Documentation.** Write `docs/SM-G970W-<build>.md` (analysis and
   validation) and add the `support/targets-v3.json` entry, in their format.
8. **Upstream.** Open a PR to `BuSung-dev/Root-My-Galaxy-Payloads` (and, if
   appropriate, report to the `BuSung-dev/Root-My-Galaxy` feed), citing this
   repository as the port source and crediting the base.

Open questions / risks:

- 4.14 versus their 5.10+ baseline: `struct` layouts differ, there is no BTF on
  this build, and the heap-grooming primitive differs.
- `MODULE_SIG_FORCE` versus the manual late-load: a working loader may need a
  call/relocation primitive this port does not currently have (data-only
  ceiling).
- Their per-boot probabilistic retries versus this port's current
  `--stop-after=verify` flow.

## Survey findings (prerequisites)

Local (WSL), present:

- `~/ghostlock/kernel/`: `Image`, `vmlinux.elf`, `kallsyms_fixed.txt`.
- `~/ghostlock/src/g9700/`: the full 4.14 ROM source, plus `out/.config` and
  `arch/arm64/configs/beyond0qlte_can_single_defconfig`.
- Tooling: `vmlinux-to-elf`, `aarch64-linux-gnu-nm`, `lz4`, `xxd`.
  Missing (needed only for the upstream BTF step): `samloader` /
  `samloader-rs`, `llvm-nm`, `pahole`, `bpftool`.
- `refs/rom-4.14-full`, `refs/kernelsu` (local, gitignored).

Device (`4.14.190-23725627-abG970WVLU9IXE1`):

- `CONFIG_MODULE_SIG_FORCE=y` (with `MODULE_SIG_ALL=y`, SHA512).
- `CONFIG_UH_RKP=y`, `CONFIG_SECURITY_DEFEX=y`, `CONFIG_FIVE=y`,
  `CONFIG_STRICT_KERNEL_RWX=y`, `CONFIG_MODVERSIONS=y`, `CONFIG_KALLSYMS_ALL=y`,
  `CONFIG_RANDOMIZE_BASE=y`.
- `CONFIG_DM_VERITY=y` (+FEC), `CONFIG_FSCRYPT_SDP=y`.
- SELinux `DEVELOP=y`; no `BOOTPARAM`, no `DISABLE`.
- `perf_event_paranoid=-1`, `security.perf_harden=1`.
- `/dev/ashmem` plus a per-boot `ashmem<bootid>` node (libcutils).
- tracefs mounted at `/sys/kernel/tracing` and `/sys/kernel/debug/tracing`.
- No BTF (`CONFIG_DEBUG_INFO=y`, `CONFIG_DEBUG_INFO_BTF` absent).

CVE presence and layout:

- `kernel/locking/rtmutex.c:1068 remove_waiter()` uses `current->pi_lock` and
  `current->pi_blocked_on = NULL` (the vulnerable form); CVE-2026-43499 is
  present and unpatched on this build.
- 4.14 `struct rt_mutex_waiter` (`kernel/locking/rtmutex_common.h:27`):
  `tree_entry@0x00`, `pi_tree_entry@0x18`, `task@0x30`, `lock@0x38`,
  `prio@0x40`, `deadline@0x48` (size 0x50) — matches
  `src/devices/beyond0q/offsets.h`.

Consequences:

- Offsets can be derived fully offline from `vmlinux.elf`, `kallsyms_fixed.txt`
  and a `struct` probe; no sampler is needed, and the upstream BTF step does not
  apply to this build.
- The app-domain route depends on the physical-P0 oracle; the base exploit is
  already cloned at `~/ghostlock/smt878u-ionstack-poc`.
- KernelSU is gated by `MODULE_SIG_FORCE`; the manual late-load loader is the
  only lead, and 4.14 has no BTF and may need a call/relocation primitive this
  data-only port does not have.
