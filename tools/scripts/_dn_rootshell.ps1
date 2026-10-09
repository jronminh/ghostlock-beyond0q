# Connect to the root shell daemon (127.0.0.1:2223) via adb forward and run a command.
# usage: powershell -File _dn_rootshell.ps1 ["id"]
param([string]$cmd = "id; echo ROOTSHELL_OK")
$adb = 'E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe'
& $adb forward tcp:2223 tcp:2223 | Out-Null
Start-Sleep -Milliseconds 300
$c = New-Object System.Net.Sockets.TcpClient
try {
  $c.Connect('127.0.0.1', 2223)
  $s = $c.GetStream()
  $w = New-Object System.IO.StreamWriter($s)
  $w.AutoFlush = $true
  $w.WriteLine($cmd)
  $w.WriteLine("exit")
  Start-Sleep -Seconds 2
  $r = New-Object System.IO.StreamReader($s)
  $buf = New-Object char[] 8192
  $n = $r.Read($buf, 0, $buf.Length)
  Write-Output ("---- response ----")
  Write-Output (-join $buf[0..([Math]::Max(0,$n-1))])
} catch {
  Write-Output ("connect failed: " + $_.Exception.Message)
} finally {
  $c.Close()
  & $adb forward --remove tcp:2223 | Out-Null
}
