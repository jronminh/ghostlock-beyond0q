#!/bin/bash
cd ~/ghostlock/bl_dec || exit 1
echo "########## vbmeta.img ##########"
python3 /mnt/e/Library/Desktop/ghostlock/parse_vbmeta.py vbmeta.img
echo
echo "########## abl.elf : ELF program headers ##########"
readelf -l abl.elf 2>&1 | head -30
echo
echo "########## abl.elf : broad keyword scan ##########"
for kw in download Download Odin ODIN fastboot Android mobile boot unlock Bootloader SECURE 'oem' 'KG' 'FRP' 'customization' 'Odin'; do
  n=$(strings -a -n 3 abl.elf | grep -c -i -- "$kw")
  echo "  $kw : $n"
done
echo
echo "########## abl.elf : interesting strings (sample) ##########"
strings -a -n 5 abl.elf | grep -iE 'download mode|fastboot|android boot|bootloader|Odin|secure boot|unlock|verity|dm-verity|avb|vbmeta|slot' | sort -u | head -50
echo
echo "########## xbl_config.elf : first 40 strings ##########"
strings -a -n 5 xbl_config.elf | head -40
