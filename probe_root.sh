#!/system/bin/sh
echo "== id =="
id
echo "== selinux ctx =="
cat /proc/self/attr/current 2>&1
echo "== getenforce =="
getenforce
echo "== kptr_restrict =="
cat /proc/sys/kernel/kptr_restrict
echo "== kallsyms (addr real if root) =="
head -n 3 /proc/kallsyms
echo "== root-only dirs =="
ls -la /data/adb 2>&1
ls -d /data/misc /data/system /data/vendor 2>&1
echo "== /data/misc listing =="
ls /data/misc 2>&1 | head -8
echo "== /proc/1 (init) =="
ls -l /proc/1/exe 2>&1
echo "== write /data =="
echo root_can_write > /data/local/tmp/rootfs_proof && echo WRITE_OK
echo "== chmod/chown =="
touch /data/local/tmp/rootfile; chmod 400 /data/local/tmp/rootfile; chown 0:0 /data/local/tmp/rootfile; ls -l /data/local/tmp/rootfile
echo "== modules sig / kallsyms of module funcs =="
grep -w commit_creds /proc/kallsyms 2>&1
echo "== caps =="
cat /proc/self/status | grep -a -E "Cap|Uid|Gid"
echo "== DONE =="
