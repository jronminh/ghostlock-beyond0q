#!/system/bin/sh
echo "== sizes =="
ls -l /dev/block/by-name/param /dev/block/by-name/persistent
echo "== strings in param (search) =="
dd if=/dev/block/by-name/param 2>/dev/null | strings | grep -i -n -e XAC -e BADGE -e OEM -e UNLOCK -e KNOX -e KG_ | head -30
echo "== strings in persistent (search) =="
dd if=/dev/block/by-name/persistent 2>/dev/null | strings | grep -i -n -e XAC -e OEM -e UNLOCK -e KNOX -e KG_ | head -20
echo "== param first 128 bytes =="
dd if=/dev/block/by-name/param bs=128 count=1 2>/dev/null | od -An -tx1
echo "== /proc/cmdline =="
cat /proc/cmdline | tr ' ' '\n' | grep -i -e oem -e unlock -e kg -e warranty -e knox -e bootloader | head
echo DONE
