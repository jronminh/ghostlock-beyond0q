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
