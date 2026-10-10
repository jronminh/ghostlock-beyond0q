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
| 4G data in VN | ✅ works (insert SIM + set the carrier APN manually) |
| VoLTE / VoWiFi | ⚠️ not provisioned by the Canada CSC; force with `persist.dbg` overrides (may only surface the toggle — IMS registration can still fail without a VN carrier config) |
| 5G | ❌ S10e is 4G only |
| Voice calls | ⚠️ if VoLTE can't register and 2G/3G are gone ⇒ calls may fail |

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
- The live property service rewrites the file on changes/shutdown, so **restart hard**
  (the `reboot(2)` syscall — `tools/scripts/hreboot.c`) so it cannot clobber the append;
  `sync()` first.

Once the props are set, reboot and enable
*Settings → Connections → Mobile networks → VoLTE calls*.

## IMS + data APN (Viettel / VinaPhone / MobiFone)
Add manually in *Settings → Connections → Mobile networks → Access Point Names*:
- the carrier **internet (data)** APN (e.g. `v-internet` / `m3-internet` / `m-wap`),
- an **IMS** APN (Type = `ims`) if VoLTE is used.

## Root
Root is **per boot** (locked bootloader + RKP; no persistent root — see
`docs/KSU_ROOT_FINDINGS.md`), and it is a **kernel-domain** root (`u:r:kernel:s0`) —
powerful for kernel work, but SELinux blocks userspace property/Settings writes.
Re-arm each boot with `scripts/enable_vn.ps1` (host) or `scripts/vn_volte.sh` (device).
