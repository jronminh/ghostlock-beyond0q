#!/bin/bash
S=/root/ghostlock/src/g9700
O=$S/out
LOG=/root/ghostlock/kbuild.log
echo "== start full kernel build (gcc) $(date) ==" > "$LOG"
make -C "$S" O="$O" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  CC=aarch64-linux-gnu-gcc LD=aarch64-linux-gnu-ld \
  -j"$(nproc)" Image 2>&1 | tee -a "$LOG" | tail -60
echo "BUILD_RC=${PIPESTATUS[0]}" | tee -a "$LOG"
echo "== System.map ==" >> "$LOG"
ls -la "$O/System.map" "$O/vmlinux" 2>&1 | tee -a "$LOG"
grep -w sig_enforce "$O/System.map" 2>/dev/null | tee -a "$LOG"
