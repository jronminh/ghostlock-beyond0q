#!/system/bin/sh
echo "== remount rw / =="
mount -o remount,rw / 2>&1
echo "rc=$?"
grep -w " / " /proc/mounts
echo "== write test on / =="
touch /gl_rw_test 2>&1 && echo WRITE_OK || echo WRITE_FAIL
ls -l /gl_rw_test 2>&1
echo "== sys rw remount test (system-as-root) =="
mount -o remount,rw /system 2>&1; echo "rc=$?"
echo "== verify setuid support: create setuid copy of toybox on / =="
cp /system/bin/toybox /gl_suid_test 2>&1 && chmod 4755 /gl_suid_test && ls -l /gl_suid_test 2>&1
echo "== run as shell should be uid 2000; we are root here =="
id
echo DONE
