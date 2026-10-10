#!/system/bin/sh
# vn_volte.sh — enable VoLTE/VoWiFi overrides for a foreign (Vietnam) SIM on the
# Canada SM-G970W (CSC XAC). Run as ROOT.
#
# The `persist.*` props survive reboot (set once). The phone still needs a VN SIM
# inserted, the carrier APN, and the VoLTE setting enabled afterwards.

setprop persist.dbg.volte_avail_ovr 1
setprop persist.dbg.vt_avail_ovr 1
setprop persist.dbg.wfc_avail_ovr 1
setprop persist.dbg.ims_volte_enable 1
setprop persist.radio.calls.on.ims 1
setprop persist.radio.jbims 1
setprop persist.dbg.volte_avail_ovr 1

echo "== applied =="
for p in persist.dbg.volte_avail_ovr persist.dbg.vt_avail_ovr \
         persist.dbg.wfc_avail_ovr persist.dbg.ims_volte_enable \
         persist.radio.calls.on.ims persist.radio.jbims; do
  printf '%s=%s\n' "$p" "$(getprop $p)"
done
echo "(reboot, then enable 'VoLTE calls' in Settings; add the IMS + data APN)"
