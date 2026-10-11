#!/system/bin/sh
# root_tweaks.sh - "group /data tweaks" via DEFEX-safe root.
#
# Run as root through the kernel-domain channel (mpnl rcmd -> sh -c). DEFEX blocks
# root from exec'ing non-safeplace paths (e.g. /system/bin/settings is a script),
# so everything here goes through safeplace binaries: `cmd` (the service
# dispatcher) and `setprop`. See docs/DEFEX_BYPASS.md.
#
# Usage:   sh /data/local/tmp/root_tweaks.sh [density_px]
# Defaults: density 420, animations 0.5.

DENSITY="${1:-420}"

echo "== root_tweaks =="
echo "id=$(id)"

# --- DPI ---
cmd window density "$DENSITY" >/dev/null 2>&1 && echo "density -> $DENSITY"
# --- animations (faster UI) ---
cmd settings put global window_animation_scale 0.5
cmd settings put global transition_animation_scale 0.5
cmd settings put global animator_duration_scale 0.5
echo "anim = $(cmd settings get global window_animation_scale)/$(cmd settings get global transition_animation_scale)/$(cmd settings get global animator_duration_scale)"
# --- misc quality-of-life (examples; comment out to taste) ---
cmd settings put system screen_off_timeout 600000          # 10 min
cmd settings put secure adaptive_sleep 0 2>/dev/null
cmd settings put global development_settings_enabled 1 2>/dev/null
# --- property-based tweaks (also work, and persist via persistent_properties) ---
setprop persist.dbg.volte_avail_ovr 1 2>/dev/null
echo "volte_ovr = $(getprop persist.dbg.volte_avail_ovr)"

echo "== debloat (list candidates; disable with: cmd package disable-user <pkg>) =="
for p in com.facebook.katana com.facebook.system com.samsung.android.bixby.agent \
         com.samsung.android.game.gamehome com.samsung.android.app.spage; do
  if cmd package path "$p" >/dev/null 2>&1; then
    echo "present: $p"
  fi
done
echo "== done =="
