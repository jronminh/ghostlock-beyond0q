# enable_vn.ps1 — re-root the Samsung SM-G970W (glA driver) and apply the Vietnam
# VoLTE overrides in one go. Requires the session tooling on /data/local/tmp
# (glA21, slideprobe, pwn2, mphelper) and a VN SIM inserted.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\enable_vn.ps1
param(
  [string]$Adb = "E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe",
  [string]$Gl  = "/data/local/tmp/glA21",
  [string]$Mp  = "/data/local/tmp/mphelper"
)

function Die($m) { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Adb)) { Die "adb not found: $Adb" }

& $Adb wait-for-device

Write-Host "[1/5] warming payload..."
& $Adb shell "$Mp >/dev/null 2>&1 & sleep 1; for p in `$(pidof mphelper); do kill -9 `$p 2>/dev/null; done; echo warm" | Out-Null

Write-Host "[2/5] slideprobe..."
$sp = (& $Adb shell "timeout 70 /data/local/tmp/slideprobe") -join "`n"
$m = [regex]::Match($sp, 'IP\s+([0-9a-fA-F]+)bd4')
if (-not $m.Success) { Die "could not find slide IP in slideprobe output" }
$low = [Convert]::ToUInt32($m.Groups[1].Value.Substring($m.Groups[1].Value.Length - 6), 16)
# slide = (low32 - 0x08000000) - 0x3bd4
$slide = $low - 0x08000000 - 0x3bd4
if ($slide -lt 0) { $slide += 0x1000000 }
$slideHex = ("0x{0:x}" -f $slide)
Write-Host "      slide = $slideHex"

Write-Host "[3/5] fops redirect + write modprobe_path + SELinux off..."
$run = & $Adb shell "env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 SLIDE=$slideHex MP_PATH=$Mp timeout 150 $Gl --stop-after=verify --log=info"
$run | Select-String -Pattern 'modprobe_path|STOP_VERIFY|ONLY_FOPS|FAIL|retval' | ForEach-Object { Write-Host "      $_" }
if (-not ($run -match 'selinux_off=1')) { Write-Host "      (warning) selinux_off not seen - walk may have failed; re-run if needed" -ForegroundColor Yellow }

Write-Host "[4/5] trigger root helper..."
& $Adb shell "chmod 755 /data/local/tmp/vn_volte.sh; rm -f /data/local/tmp/rout; /data/local/tmp/pwn2 >/dev/null 2>&1; sleep 2" | Out-Null

Write-Host "[5/5] apply VoLTE overrides via the root channel..."
& $Adb shell "echo 'sh /data/local/tmp/vn_volte.sh' > /data/local/tmp/rcmd; sleep 4; cat /data/local/tmp/rout"
Write-Host ""
Write-Host "Done. Reboot, then enable 'VoLTE calls' in Settings and add the IMS + data APN." -ForegroundColor Green
