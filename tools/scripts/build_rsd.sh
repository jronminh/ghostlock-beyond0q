#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' \
  tools/_rsd.c src/primitives/rootshell.c -o rsd_diag -static
file rsd_diag
ls -l rsd_diag
