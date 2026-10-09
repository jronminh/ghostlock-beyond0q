#!/bin/bash
cd ~/ghostlock/bl_dec || exit 1
for f in vbmeta.img xbl_config.elf abl.elf xbl.elf; do
  echo "=========================== $f ==========================="
  echo "size: $(stat -c%s $f)"
  echo "--- head 128 bytes ---"
  xxd -l 128 "$f"
  echo "--- strings count ($(strings -a -n 4 "$f" | wc -l)) ---"
  strings -a -n 6 "$f" | sed -n '1,15p'
  echo
done
