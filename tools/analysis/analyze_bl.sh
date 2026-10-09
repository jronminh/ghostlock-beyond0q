#!/bin/bash
cd ~/ghostlock/bl_dec || exit 1
echo "===== sha256 (bootloader images) ====="
sha256sum vbmeta.img xbl.elf xbl_config.elf abl.elf
echo
echo "===== vbmeta.img (AVB) ====="
python3 /mnt/e/Library/Desktop/ghostlock/parse_vbmeta.py vbmeta.img
echo
echo "===== abl.elf : unlock / token / knox / frp strings ====="
strings -a -n 4 abl.elf | grep -iE 'oem.?lock|unlock|token|knox|kg.?state|prenormal|\brmm\b|\bfrp\b|secure.?boot|odin|devinfo|warranty|carrier|download' | sort -u | head -80
echo
echo "===== xbl_config.elf : kaslr / mem / boot strings ====="
strings -a -n 4 xbl_config.elf | grep -iE 'kaslr|slide|random|kernel|ddr|mem|base|aboot|vbmeta|avb' | sort -u | head -60
echo
echo "===== xbl_config.elf : all strings count ====="
strings -a -n 4 xbl_config.elf | wc -l
