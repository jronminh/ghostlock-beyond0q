#!/bin/bash
cd /root/ghostlock/ghostlock-oneplus || exit 1
aarch64-linux-gnu-gcc -fsyntax-only -O2 -w -include stddef.h \
  -DKERNELSNITCH_THRESHOLD_MULT=30 -Isrc/core -Isrc/devices \
  -DTARGET_CONFIG_H='"target.h"' \
  src/core/fops.c src/core/util.c src/core/main.c && echo SYNTAX_OK
