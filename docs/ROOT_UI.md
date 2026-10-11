# ROOT_UI.md — an on-device control surface for the transient root

The exploit gives a **per-boot, uid-0 userspace root** reached through a
`modprobe_path` helper (`src/primitives/mpnl.c`). Typing commands over `adb`
every time is fine for development, but the goal here is a **user-facing control
panel** that runs *on the phone*. This document describes the design, how to arm
it, the API, and the security model.

## TL;DR

* The root helper `mpnl` is now also a **small HTTP server on
  `127.0.0.1:8080`** that serves a single-page app embedded in the binary.
* Open `http://127.0.0.1:8080/` in **Chrome on the device** — no PC, no APK.
* Buttons run root commands through the **safeplace** `/system/bin/sh` +
  `/system/bin/cmd`, read/write properties, and list/disable packages.
* **Arming still needs one adb pass per boot** (the exploit itself must win the
  futex PI walk; see "Arming from the phone" below). The UI has a status panel
  that tells you whether root is currently armed.

## Why a daemon + embedded web UI

Constraints that shaped the design:

| constraint | consequence |
|---|---|
| fscrypt: a kernel-spawned process **cannot create new `/data` files** | the HTML/JS/CSS must be **embedded in the binary** (not read from disk) |
| DEFEX: root may only `execve` **safeplace** paths | the daemon runs commands via `/system/bin/sh -c` and prefers `/system/bin/cmd` over wrapper scripts |
| SELinux: raw `selinux_enforcing=0` is invisible to userspace | `mpnl` toggles `/sys/fs/selinux/enforce` 1→0 once at start (with `policydb.permissive_map` patched by the driver) so `setprop` really works |
| no APK / no signature | serve over loopback; the browser is the "app" |

The daemon is the *same* process the kernel already runs for us (the
`modprobe_path` helper), so nothing new has to be spawned by an unsigned binary.

## Architecture

```
        driver (glXX, run from a shell)
             │  PI walk + fops redirect
             │  write modprobe_path = /data/local/tmp/mpnl
             │  patch policydb.permissive_map (kernel type permissive)
             ▼
   exec /data/local/tmp/pwn2  (4x0xFF)  ─▶ kernel request_module()
             │
             ▼  call_usermodehelper
        /data/local/tmp/mpnl   (uid 0, u:r:kernel:s0, full caps)
             ├─ sync_selinux()      # echo 1 → 0 into /sys/fs/selinux/enforce
             ├─ HTTP  127.0.0.1:8080  ──  webui.html (embedded)  ── Chrome (device)
             └─ file channel: /data/local/tmp/rcmd → rout   (legacy, for scripts)
```

* `src/primitives/webui.html` — the single-page UI (source of truth).
* `src/primitives/mpnl.c` — the daemon: HTTP server + `/api/*` handlers + the
  legacy file channel.
* `tools/build14.sh` — runs `xxd -i webui.html > webui_html.h` (gitignored) then
  compiles `mpnl` static; the UI is embedded via `#include "webui_html.h"`.
* `scripts/arm_root.sh` — host-side one-shot armer (slide probe → driver →
  trigger → verify).

## HTTP API

All `/api/*` calls require a **per-boot random token**; it is injected into the
served page (`__GL_TOKEN__`) and sent back in the `X-GL-Token` header (or `?t=`).
`GET /` needs no token (it only returns HTML, and CORS stops another origin from
reading the token out of it).

| method | path | params | result |
|---|---|---|---|
| GET | `/` | — | the UI (HTML) |
| POST | `/api/status` | — | `{gl,version,uid,euid,gid,pid,ctx,enforce,selinux,boot_id}` |
| POST | `/api/exec` | `cmd` | `{rc,out}` — runs `sh -c cmd` as root |
| POST | `/api/prop` | `op=get\|set`, `name`, `value` | `{rc,name,value}` |
| POST | `/api/pkg` | `op=list\|disable\|enable`, `pkg` | `{rc,out}` |

Example from a shell on the device:

```sh
P=$(curl -s http://127.0.0.1:8080/); T=$(printf '%s' "$P" | tr -d '\r' \
  | awk -F'"' '/TOKEN =/{print $2; exit}')
curl -s -H "X-GL-Token: $T" http://127.0.0.1:8080/api/status
curl -s -X POST -H "X-GL-Token: $T" --data 'cmd=id; getenforce' \
  http://127.0.0.1:8080/api/exec
```

## Security model

The daemon is **root** and bound to loopback only. Two mitigations:

1. **Loopback bind** (`127.0.0.1`) — not reachable from the network.
2. **Per-boot token** — `/api/*` require it. A cross-origin web page cannot read
   the token (our responses carry no `Access-Control-Allow-Origin` for other
   origins), so it cannot drive root. A *native* app with INTERNET can still read
   `/` and get the token; that is accepted for this research device (such an app
   could already run the exploit from adb). Add a user PIN later if needed.

## Usage

On the device (after arming, see below): open **Chrome → `127.0.0.1:8080`**.
The Status card shows uid / SELinux / context, and whether the daemon is up.

## Arming from the phone (open question)

Arming requires running the **driver binary** once per boot and then executing
`pwn2`. Today that is done from a shell over `adb`; the UI itself cannot start
the exploit. Notes on doing it on-device:

* The exploit is a **normal (non-root) userspace** program: it does futex PI /
  `pselect` / `setsockopt` / `perf_event_open` and opens **`/dev/ashmem`** (with a
  per-boot `ashmem<bootid>` name). It does **not** open `/sys/kernel/config`: the
  "configfs" names refer to kernel `.text` targets it redirects the ashmem fops to
  (`configfs_read_file` / `configfs_bin_write_iter`), so userspace only needs the
  ashmem device.
* An app could, in principle, ship the driver as a native lib, extract it to its
  private `/data` dir, and `exec` it (app data dirs are executable; a
  non-root/app-domain exec of *`/data`* is allowed — unlike root/DEFEX). The two
  gates for the `untrusted_app` domain were checked against the on-device split
  policy (`/system/etc/selinux/plat_sepolicy.cil`, Android 12):
  1. **`/dev/ashmem`** — `crw-rw-rw-`; the per-boot node is
     `ashmem_libcutils_device`, which `domain` may `open`
     (`(allow domain ashmem_libcutils_device (chr_file (... open ...)))`) → an app
     *can* open it.
  2. **`perf_event_open`** — allowed for `shell` and `runas_app`
     (`(allow shell self (perf_event (open kernel read write)))`) but there is
     **no `(allow untrusted_app ... perf_event ...)` rule**. `perf_event_paranoid=-1`
     is permissive at the kernel level, so **SELinux is the wall**: a normal app
     cannot do the `perf_event_open()` the walk needs for its page leak.
  ⇒ On-device arming from a plain APK is **blocked** unless the process runs in
  `shell`/`runas_app` (i.e. via adb or `run-as`).
* Until that changes, the workflow is: **arm once per boot from adb**
  (`scripts/arm_root.sh`), then use the UI purely on-device. The Status panel in
  the UI answers "is root armed right now?" (`/api/status`).

## Build

```
bash tools/build14.sh /tmp/glU2
# -> glU2_a64 (driver), glU2_dnroot_a64 (UMH payload), glU2_mpnl_a64 (daemon+UI)
```

`glU2_mpnl_a64` is pushed to `/data/local/tmp/mpnl`; the driver is pointed at it
with `MP_PATH=/data/local/tmp/mpnl`.
