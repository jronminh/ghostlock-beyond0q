#!/system/bin/sh
echo "== size of persistent =="
ls -l /dev/block/by-name/persistent
echo "== first 512 bytes (hex) =="
dd if=/dev/block/persistent bs=512 count=1 2>/dev/null | od -An -tx1 | head -16
echo "== first 512 bytes (ascii) =="
dd if=/dev/block/persistent bs=512 count=1 2>/dev/null | od -An -c | head -16
echo DONE
