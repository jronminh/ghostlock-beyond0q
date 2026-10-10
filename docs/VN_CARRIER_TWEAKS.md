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

## Enable VoLTE (run as root — `persist.*` props survive reboot, set once)
```sh
setprop persist.dbg.volte_avail_ovr 1
setprop persist.dbg.vt_avail_ovr 1
setprop persist.dbg.wfc_avail_ovr 1
setprop persist.dbg.ims_volte_enable 1
setprop persist.radio.calls.on.ims 1
setprop persist.radio.jbims 1
```
Or run `scripts/vn_volte.sh` (on the device: `/data/local/tmp/vn_volte.sh`).
Then **reboot** and enable *Settings → Connections → Mobile networks → VoLTE calls*.

## IMS + data APN (Viettel / VinaPhone / MobiFone)
Add manually in *Settings → Connections → Mobile networks → Access Point Names*:
- the carrier **internet (data)** APN (e.g. `v-internet` / `m3-internet` / `m-wap`),
- an **IMS** APN (Type = `ims`) if VoLTE is used.

## Root
Root is **per boot** (locked bootloader + RKP; no persistent root — see
`docs/KSU_ROOT_FINDINGS.md`). Re-run the exploit each boot; then run `vn_volte.sh`.
The `persist.*` props only need setting **once**.
