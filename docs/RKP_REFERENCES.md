# RKP / KDP references (for SM-G970W, Snapdragon 855 / msmnile, ROM 4.14.190)

Collected references on Samsung **RKP** (Real-time Kernel Protection), **KDP** (Kernel
Data Protection), **JOPP/ROPP**, **DEFEX** — the mitigations that sit *above* the kernel
and constrain what an EL1 (kernel) compromise can do. Each entry says why it matters for
**this** device / ROM. See also `docs/KSU_ROOT_FINDINGS.md` (§10-§14) for what we observed
on the device.

## Primary technical references

| Source | What it gives | Link |
|---|---|---|
| **A Samsung RKP Compendium** — A. Adamski / Longterm Security (Jan 2021) | The most complete public description of RKP internals: uH framework, memlists/sparsemaps, `physmap`/`ro_bitmap`/`dbl_bitmap`, `APP_INIT`/`APP_RKP`, `uh_call`=HVC, JOPP/ROPP/KDP; also **how to extract the RKP binary** (Exynos vs Snapdragon). | https://blog.impalabs.com/2101_samsung-rkp-compendium.html (mirror: https://blog.longterm.io/samsung_rkp.html) |
| **Attacking Samsung RKP** — A. Adamski (Nov 2021) | Three RKP vulnerabilities (EL2 memory remap as writable, exec pages, RO memory write), exploitation, patches. Methodology: with arbitrary kernel R/W, drive RKP via `uh_call`. | https://blog.impalabs.com/2111_attacking-samsung-rkp.html |
| **SELinux RKP misconfiguration on Samsung S20** — V. Nikolenko / DUASYNT (Aug 2020) | SVE-2019-15998: the patch marks `selinux_enforcing` / `ss_initialized` as `__kdp_ro` and hands them to RKP via `kdp_init_struct`; before the patch they could be zeroed to disable SELinux. **Directly relevant to our §12/§14.** | https://duasynt.com/blog/samsung-s20-rkp-selinux-disable |
| **From graphics driver to root shell** — Jamf Threat Labs (Jul 2026) | Modern full chain: RKP/KDP/DEFEX/JOPP-ROPP as four walls, and the **GPU-DMA bypass** (CVE-2025-21479, Qualcomm KGSL) → "Dirty Pagetable" → disable SELinux → inject into `init`. Explains *why* the whole stack can be bypassed. | https://www.jamf.com/blog/samsung-kernel-protections-gpu-dma-bypass/ |
| **Lifting the (Hyper) Visor: Bypassing Samsung's RKP** — G. Beniamini / Project Zero (Feb 2017) | The original public RKP bypass (Exynos S7); HYP 101 background; design-improvement suggestions Samsung later adopted (WXN, EL1 traps, etc.). | https://projectzero.google/2017/02/lifting-hyper-visor-bypassing-samsungs.html |
| **TZ-RKP: Real-time Kernel Protection from the ARM TrustZone** — Azab et al., ACSAC/CCS 2014 | The academic origin of RKP (TrustZone-based kernel protection). | https://wenboshen.org/publications/papers/tz-rkp-ccs14.pdf |
| **On emulating hypervisors: a Samsung RKP case study** — A. Thallas, Phrack #70 | Emulating the RKP hypervisor for analysis. | http://www.phrack.org/issues/70/10.html |
| **Reversing Samsung's H-Arx Hypervisor Framework** — DayZeroSec (2025) | The successor framework to uH (S20+), unifying RKP across Exynos/Snapdragon. | https://dayzerosec.com/blog/2025/03/08/reversing-samsungs-h-arx-hypervisor-part-1.html |
| **Samsung Knox: RKP overview** | Vendor description (high level). | https://www.samsungknox.com/en/blog/knox-deep-dive-real-time-kernel-protection-rkp |

## How it works (condensed, from the Compendium)

- RKP is a **security hypervisor at EL2**; the kernel is EL1. When the kernel does
  something forbidden the CPU traps to EL2 and RKP blocks it.
- Enforcement uses the **stage-2 translation** (VA→IPA→PA): RKP marks sensitive physical
  pages read-only in stage 2, so *CPU* accesses fault regardless of the stage-1 (kernel)
  page tables.
- It runs as an "app" of the **uH micro-hypervisor**: static/dynamic heaps, `memlist`s
  (address ranges) and `sparsemap`s (addr→value): `physmap` (page type), `ro_bitmap`
  (stage-2 read-only), `dbl_bitmap` (double-map tracking), `protected_ranges`.
- Kernel↔RKP interface: `uh_call(...)` = `HVC` instruction; app IDs `APP_INIT`/`APP_RKP`
  (`UH_APPID`); our ROM's kernel side is `include/linux/rkp.h` + `init/main.c:rkp_init()`.
- Protections: **page tables** RO + traps on VM system registers; `.rodata` RO;
  `cred`, `task_security_struct`, `vfsmount` on RO pages; `selinux_enforcing`/`ss_initialized`
  (see below); **JOPP** (indirect-call CFI, magic `0xbe7bad`, `rkp_cfp.S`); **ROPP**
  (return-address CFI with a per-thread key, master key in `DBGBCR5_EL1` on production).

## Device matrix (from the Compendium) — ours is the strictest row

| Device class | Region | JOPP | ROPP | KDP |
|---|---|---|---|---|
| High-end | United States | Yes | Yes | Yes |
| High-end | International | Yes | No | Yes |

`SM-G970W` is the **US/Canada high-end (Snapdragon)** variant ⇒ **JOPP + ROPP + KDP all on**.
This matches what we already hit: `rkp_cfp`/springboards, the ROPP thread key, and the
`cred_jar_ro` / "RKP CRED PROTECTION VIOLATION" panic.

## Snapdragon-specific fact (important for us)

On **Snapdragon** devices RKP is **not** a standalone `uh.elf`. It is one segment of the
**Qualcomm Hypervisor Execution Environment (QHEE)** image inside the **`hyp` partition**,
shipped in the `BL_*.tar` blobs of a firmware update (and QHEE sets the page tables and the
exception vector, notifying uH on traps). ⇒ reversing it is harder than on Exynos, and the
`hyp` partition is where to look for the actual binary.

## SELinux-specific: `selinux_enforcing` and KDP (SVE-2019-15998)

The DUASYNT note shows that when Samsung *patched* this area they:

```c
int selinux_enforcing __kdp_ro;   // placed in .kdp_ro (read-only from EL1 via RKP/KDP)
extern int ss_initialized __kdp_ro;
...
cred.selinux.selinux_enforcing_va = (u64)&selinux_enforcing;   // handed to RKP
cred.selinux.ss_initialized_va    = (u64)&ss_initialized;
```
and that on the affected (pre-patch) S20 the variables were **not** protected, so SELinux
could be disabled by a single kernel write.

**Our ROM (this repo's source, `g9700`):**
```c
// security/selinux/hooks.c
int selinux_enforcing;                       // NOT __kdp_ro   -> writable, no panic
int selinux_enforcing_boot __kdp_ro;         // protected
int selinux_enabled __kdp_ro = 1;            // protected
struct task_security_struct init_sec __kdp_ro;
// init/main.c
cred.selinux.ss_initialized_va = (u64)&ss_initialized;   // ss_initialized is given to RKP
```
So on **this** device `selinux_enforcing` is **not** KDP-protected (consistent with
`docs/KSU_ROOT_FINDINGS.md`: writing it flips `getenforce` to *Permissive* and does **not**
panic). At the same time `selinux_enabled` and `ss_initialized` *are* protected — which is a
likely reason an EL1-only "set `selinux_enforcing=0`" does not translate into working
userspace perms (we still get `avc ... permissive=0` on `setprop`; see §14).

## The realistic full-bypass direction (Jamf 2026)

All four walls rest on one assumption: **memory modifications pass through the CPU**.
A **DMA-capable peripheral (the GPU / Qualcomm KGSL)** writes to RAM over the bus without
going through the CPU's stage-2 translation ⇒ RKP/KDP never see it. The published chain
(CVE-2025-21479) is: GPU DMA arbitrary phys R/W → "Dirty Pagetable" self-referencing PTE
(CPU-speed R/W) → zero `selinux_state` enforcing → inject code into `init`'s exec pages via
its PLT (DEFEX allowlists `init`, and PLT entries are plain data, so JOPP does not cover
them). ⇒ For a *true* root on this Snapdragon device, the interesting front is the GPU
(KGSL/adreno-6xx) DMA path, not more EL1 tricks.

## On-device extraction

The kernel-domain root can read block devices, so we pulled this device's own RKP image:

```
$ ls -la /dev/block/by-name/hyp     ->  /dev/block/sdd31   (2048 sectors = 1 MiB)
$ dd if=/dev/block/by-name/hyp of=<warmed file> bs=1M   ->  1 MiB
```

`readelf` on the dump:

- **ELF64 AArch64**, type EXEC, entry **`0x85710000`**, no section headers (stripped).
- Program headers: `LOAD @ 0x85700000` (filesz `0xf23d`) and `LOAD @ 0x85710000`
  (filesz `0x6f188`, memsz `0x24c000`), `RWE` — the uH/RKP image region.
- `strings` shows the log strings are **hashed placeholders** `RKP_<sha256[:8]>`
  (e.g. `RKP_d8f93793`, `RKP_a40b50bd %p`, `RKP_f6c105df %p %p %p %p`), exactly as the
  Compendium describes.

**Cross-reference / key result:** our binary contains **`RKP_4acbd6db%lxRKP_00950f15%lx`**,
which is the string emitted by `rkp_s2_range_change_permission` in the *Attacking Samsung
RKP* article ⇒ **this device's RKP shares the codebase** with the (Exynos, unlocked)
research target, so the published function/log-string analysis largely applies. The
original log strings can be recovered by hashing candidates (`sha256(s)[:8]`).

The dump is kept **local only** (`tools/hyp.bin`, gitignored — it is a signed
Samsung/TZ blob and must not be published).

## Next concrete steps on-device

1. **Recover RKP log strings**: hash candidate strings (`sha256(s)[:8]`) from the
   Compendium / Attacking-RKP articles and match the `RKP_*` placeholders in the dump to
   rebuild a partial symbol map for *this* image.
2. **Check `.kdp_ro`**: locate the `.kdp_ro` section range in the device kernel and confirm
   which of `selinux_enforcing` / `selinux_enabled` / `ss_initialized` fall inside it
   (matches the source reading above empirically).
3. **Study KGSL on msmnile** (adreno 640 / `msm-4.14` kgsl) for a DMA/page-table-update path
   comparable to CVE-2025-21479 — the modern bypass route.
