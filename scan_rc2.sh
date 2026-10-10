#!/system/bin/sh
DIRS="/system/etc/init /system/etc/init/hw /vendor/etc/init /vendor/etc/init/hw /product/etc/init"
echo "== myfilter / DownFilters =="
grep -rn -e myfilter -e DownFilter -e MyFilter $DIRS 2>/dev/null
echo
echo "== perf_harden / perf_lsm =="
grep -rn -e perf_harden -e perf_lsm $DIRS 2>/dev/null
echo
echo "== overlays / recovery-persist / dexopt ctrl =="
grep -rn -e "/data/overlays" -e recovery-persist -e dexopt $DIRS 2>/dev/null | head -30
echo
echo "== files using u:r:su:s0 =="
grep -rln "u:r:su:s0" $DIRS 2>/dev/null
echo
echo "== lines around DownFilters dirs =="
grep -rn -A6 -B2 "DownFilters" $DIRS 2>/dev/null | head -60
echo DONE
