#!/bin/bash
set -e
SRC=/root/ghostlock/src/g9700
DST=/mnt/e/Library/Desktop/ghostlock-beyond0q/refs/rom-4.14-full
mkdir -p "$DST"
echo "copying full kernel source: $SRC -> $DST"
cp -a "$SRC/." "$DST/"
echo "DONE"
du -sh "$DST"
ls "$DST" | head
