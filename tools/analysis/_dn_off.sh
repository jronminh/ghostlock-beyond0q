#!/bin/bash
G="$HOME/ghostlock/ghostlock-oneplus/src"
echo "=== devices/offsets.h ==="
cat -n "$G/devices/offsets.h"
echo
echo "=== select_offsets / OFFSETS_ENTRY usage ==="
grep -rn -e OFFSETS_ENTRY -e select_offsets -e active_offsets "$G/core" "$G/devices" | head -40
