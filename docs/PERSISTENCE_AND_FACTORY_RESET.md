# Persistence, factory reset, and what is *not* durable (SM-G970W)

Experiment run on-device to answer: do the reboot-durable tweaks survive a factory
reset?  Short answer: **no** — and the experiment also showed they have real
boot-time side effects.

## Where the durable tweaks live

The Vietnam-carrier/ VoLTE tweak is stored as persistent properties.  `setprop` is
blocked from the kernel-domain root (`u:r:kernel:s0`), so the value was written into
the property file directly:

```
/data/property/persistent_properties     # root:root 0600, 6724 bytes, Android protobuf
```

Read back with the kernel-domain root (`base64` via the `rcmd`/`rout` channel) and
parsed: 139 `persist.*` entries, including the six VoLTE ones

```
persist.dbg.volte_avail_ovr=1   persist.dbg.vt_avail_ovr=1   persist.dbg.wfc_avail_ovr=1
persist.dbg.ims_volte_enable=1  persist.radio.calls.on.ims=1 persist.radio.jbims=1
```

plus `persist.sys.locale=en-US`, `persist.sys.timezone=Asia/Ho_Chi_Minh`,
`persist.sys.usb.config=mtp,conn_gadget,adb`, `persist.sys.setupwizard=FINISH`,
`persist.sys.device_provisioned=1`, the `persist.sys.omc_*`/`sec_*` CSC state, etc.
`init` loads this file every boot -> "survives reboot" is just `/data` being intact.

## The experiment

1. Backup the file (base64 over the root channel) to the host.
2. Empty it in place (`: > /data/property/persistent_properties`, keeping the inode) —
   this is exactly what a factory-reset's `/data` wipe does to this file.
3. Reboot.

Result after the reboot:

```
persist.dbg.volte_avail_ovr = (empty)      # gone, did not come back
persist.sys.locale          = en-CA        # back to default (was en-US)
persist.sys.timezone        = GMT          # back to default (was Asia/Ho_Chi_Minh)
```

So everything stored in `/data/property/persistent_properties` is lost when the file
is removed and is **not** restored from anywhere else.  A real factory reset goes
further (it formats the whole `userdata` partition, and the settings DB with it).

## Observed side effect: USB/debug state

After the wipe the phone still booted, but the USB gadget no longer exposed ADB
(Windows saw MTP/WPD only; `adb devices` empty).  The USB function set at boot comes
from the **persisted** prop (`persist.sys.usb.config` -> runtime `sys.usb.config`), and
`init` only starts adbd on `on property:sys.usb.config=adb`.  With the prop gone, the
default composition had no `adb` -> adbd never started -> no adb interface.  Toggling
"USB debugging" in Developer options made the framework re-write the prop
(`mtp,conn_gadget,adb`) and adb returned.

This is a concrete demonstration that wiping persisted properties changes boot-time
behaviour, not just cosmetic values.

## Restoring

`cat backup > persistent_properties` from the kernel-domain root fails with
`Required key not available` (**fscrypt ENOKEY**): the file is under `/data/local/tmp`
and the kernel-spawned helper carries init's keyring, so it can only touch inodes whose
`i_crypt_info` is already cached (the "warm" rule).  The clean path is `setprop`
**as root after the helper has synced SELinux to permissive** — the property service
(which owns the keys) then writes the file itself.  That is what `scripts/vn_volte.sh`
does; `scripts/pptool.py` is the offline writer if you would rather patch the protobuf.

## Surviving partitions (not property sources)

Mounted and *not* wiped by a factory reset: `/persist` (sda5), `/efs` (sda9),
`/mnt/vendor/efs` (sda6), `/omr` (sda30), and `param`/`persistent`/`steady`
(sda7/14/15).  None of them is a property source for Android, so they give no
"survives factory reset" persistence for these tweaks.  (They are also the partitions
where a mistake can brick the device — read only unless you know what you are doing.)
