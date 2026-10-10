#!/system/bin/sh
DIRS="/system/etc/init /system/etc/init/hw /vendor/etc/init /vendor/etc/init/hw /product/etc/init /odm/etc/init"
echo "=== [1] on property triggers ==="
grep -rhn "^on property:" $DIRS 2>/dev/null | head -80
echo
echo "=== [2] exec lines ==="
grep -rhn "exec" $DIRS 2>/dev/null | head -50
echo
echo "=== [3] writable-path references in rc ==="
grep -rhn -e "/data/" -e "/cache/" -e "/omr/" -e "/carrier/" -e "/efs/" -e "/persist/" -e "/keydata/" -e "/sdcard" $DIRS 2>/dev/null | head -60
echo
echo "=== [4] services that run app_process/dalvikvm/sh -c ==="
grep -rhn -e "app_process" -e "dalvikvm" -e "sh -c" -e "/system/bin/sh" $DIRS 2>/dev/null | head -40
echo
echo "=== [5] imports ==="
grep -rhn "^import" $DIRS 2>/dev/null | head -40
echo DONE
