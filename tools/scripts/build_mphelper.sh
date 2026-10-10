#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' \
  tools/mphelper.c src/primitives/rootshell.c -o mphelper -static
file mphelper
ls -l mphelper
