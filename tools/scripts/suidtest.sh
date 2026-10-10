#!/system/bin/sh
echo "== /data before =="
grep " /data " /proc/mounts
echo "== remount suid =="
mount -o remount,suid /data 2>&1; echo "rc=$?"
echo "== /data after =="
grep " /data " /proc/mounts
echo "== make setuid toybox on /data =="
cp /system/bin/toybox /data/local/tmp/suidtoy 2>&1
chmod 4755 /data/local/tmp/suidtoy 2>&1
ls -l /data/local/tmp/suidtoy 2>&1
echo "== also try suid+dev on /data =="
mount -o remount,rw,suid /data 2>&1; echo "rc2=$?"
grep " /data " /proc/mounts
echo DONE
