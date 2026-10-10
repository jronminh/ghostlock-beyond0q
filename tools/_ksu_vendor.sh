#!/bin/bash
set -e
K=/root/ghostlock/_ksu
R=/root/ghostlock/src/g9700
SYM=/root/ghostlock/kernel
DST=/mnt/e/Library/Desktop/ghostlock-beyond0q/refs/kernelsu

rm -rf "$DST"
mkdir -p "$DST/bakasu" "$DST/rom"

# --- KernelSU (BakaSU/ReSukiSU) sources needed to build ---
cp -a "$K/kernel"           "$DST/bakasu/kernel"
cp -a "$K/userspace"        "$DST/bakasu/userspace"
cp -a "$K/uapi"             "$DST/bakasu/uapi"         2>/dev/null || true
cp -a "$K/scripts"          "$DST/bakasu/scripts"      2>/dev/null || true
cp -a "$K/justfile" "$DST/bakasu/" 2>/dev/null || true
mkdir -p "$DST/bakasu/docs"
cp -a "$K/docs/README.md" "$DST/bakasu/docs/" 2>/dev/null || true
cp -a "$K/kernel/setup.sh" "$DST/bakasu/setup.sh" 2>/dev/null || true
echo "BakaSU commit: $(git -C "$K" rev-parse --short HEAD 2>/dev/null) ($(git -C "$K" log -1 --format=%ci 2>/dev/null))" > "$DST/bakasu/COMMIT.txt"

# --- ROM-side build inputs ---
cp -a "$R/out/.config" "$DST/rom/out.config" 2>/dev/null || true
cp -a "$R/arch/arm64/configs/beyond0qlte_chn_open_defconfig" "$DST/rom/beyond0qlte_chn_open_defconfig" 2>/dev/null || true
cp -a "$R/build_kernel.sh" "$DST/rom/build_kernel.sh" 2>/dev/null || true
cp -a "$SYM/kallsyms_fixed.txt" "$DST/rom/kallsyms_fixed.txt" 2>/dev/null || true

echo "== DST sizes =="
du -sh "$DST" "$DST"/* 2>&1
echo "== kernelsu tree =="
find "$DST" -maxdepth 2 | sed "s#$DST#refs/kernelsu#" | sort | head -60
