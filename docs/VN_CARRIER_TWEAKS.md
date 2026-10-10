# Vietnam carrier tweaks — SM-G970W (Canada model)

Device: **SM-G970W** (Snapdragon 855 / SM8150, modem X24), CSC **XAC (Canada)**,
**4G only**. OMC (`/product/omc`) = **Canada carriers only**
(BMC BWA FIZ FMC GLW KDO MTB PCM PMB RWC SJR SOL SPC TLS VMC VTR XAC) — there is **no
Vietnam CSC**. The G970W is a Snapdragon/Canada firmware; it **cannot** run the Exynos
G970F (global/VN) firmware.

## Vietnam network facts
- **4G (LTE):** B1 (2100), B3 (1800), B8 (900) (+ B5/B7 per carrier)
- **5G:** n41 (2500), n78 (3500), n261 (mmWave)
- **2G:** shut down nationwide (from 15/9/2026); **3G** being phased out ⇒ **voice needs VoLTE**
- The G970W supports **B1/B3/B5/B7/B8** ⇒ **4G data is compatible**

## What works vs what doesn't
| Feature | Status |
|---|---|
| 4G data in VN | ✅ works (SIM + carrier APN) |
| VoLTE / VoWiFi | ✅ **works** with the `persist.dbg` overrides — verified on a **Viettel (452 04)** SIM, registered on **LTE**, despite **no Vietnam CSC** |
| 5G | ❌ S10e is 4G only |
| Voice calls | ✅ VoLTE voice works (verified on-device) |

## Enable VoLTE — status: BLOCKED by SELinux
The intended props are:
```sh
setprop persist.dbg.volte_avail_ovr 1
setprop persist.dbg.vt_avail_ovr 1
setprop persist.dbg.wfc_avail_ovr 1
setprop persist.dbg.ims_volte_enable 1
setprop persist.radio.calls.on.ims 1
setprop persist.radio.jbims 1
```
But the root obtained here runs in SELinux domain **`u:r:kernel:s0`**, and the
**property service denies `setprop` from that domain** (see
`docs/KSU_ROOT_FINDINGS.md` §14). `scripts/vn_volte.sh` therefore reports
`Failed to set property …`. There is **no Magisk-style userspace root** on this device
(locked bootloader + RKP + `user` build), so the framework props can't be set live.

### Reachable alternative: write the persisted props directly (data layer)
`setprop` is blocked, but the **persisted-property file itself is writable** by the
kernel-domain root (it is an *existing* file, so fscrypt's key is cached):

```
/data/property/persistent_properties     # root:root 0600, an Android protobuf
```

Format = a flat concatenation of entries `0a <len> 0a <namelen> <name> 12 <vallen>
<value>` (one per `persist.*` prop). Appending the six entries sets those props **on the
next boot** (init loads the file). `scripts/pptool.py` parses it and emits the append bytes:

```
python3 scripts/pptool.py dump <b64dump>     # list existing entries
python3 scripts/pptool.py mkapp  app.b64     # base64 of the 6 VoLTE entries
```

On device, as root: `base64 -d app.b64 >> /data/property/persistent_properties`.

Caveats (learned the hard way):
- **One root daemon only.** Several daemons race on `rcmd` and interleave the concurrent
  appends, which *corrupts* the protobuf (keep a backup of the original file).
- After appending, **reboot**. A plain `adb reboot` turned out to be enough — the property
  service did **not** clobber the appended entries on shutdown. (Trying to force a harder
  restart with a helper binary in `/data/local/tmp` failed for a different reason: **DEFEX**
  killed it — `defex: safeplace violation … uid=0` → SIGKILL; see
  `docs/KSU_ROOT_FINDINGS.md` §10.)

**Result (verified):** after the reboot all six props read back `=1`
(`persist.dbg.volte_avail_ovr`, `persist.dbg.vt_avail_ovr`, `persist.dbg.wfc_avail_ovr`,
`persist.dbg.ims_volte_enable`, `persist.radio.calls.on.ims`, `persist.radio.jbims`), and
the rest of the file parsed fine (`persist.sys.locale=vi-VN`). On a **Viettel (452 04)** SIM
the phone registered on **LTE** and **VoLTE calls work** (confirmed on-device) — the
overrides alone were sufficient; **no Vietnam CSC was needed**.

Then reboot and enable *Settings → Connections → Mobile networks → VoLTE calls*.

## Durability
Writing the props into `/data/property/persistent_properties` is exactly how a normal
`setprop persist.*` is stored, so durability is the same:
- ✅ **survives reboot** and normal use/updates — init loads the file every boot;
- ✅ **self-sustaining:** once loaded, the props are in the property service's in-memory
  map, so any later rewrite of the file keeps them;
- ❌ lost on **factory reset / data wipe** (`/data` erased) or a **firmware flash** — just
  re-apply afterwards;
- root is only needed to *write* the file once; using the props needs no root.

## IMS + data APN (Viettel / VinaPhone / MobiFone)
Add manually in *Settings → Connections → Mobile networks → Access Point Names*:
- the carrier **internet (data)** APN (e.g. `v-internet` / `m3-internet` / `m-wap`),
- an **IMS** APN (Type = `ims`) if VoLTE is used.

## Root
Root is **per boot** (locked bootloader + RKP; no persistent root — see
`docs/KSU_ROOT_FINDINGS.md`), and it is a **kernel-domain** root (`u:r:kernel:s0`) —
powerful for kernel work, but SELinux blocks userspace property/Settings writes.
Re-arm each boot with `scripts/enable_vn.ps1` (host) or `scripts/vn_volte.sh` (device).
