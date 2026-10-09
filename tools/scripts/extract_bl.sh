#!/bin/bash
cd ~/ghostlock || exit 1
echo "=== FirmwareInfo ==="
cat _FirmwareInfo_Samfw.com.txt 2>/dev/null
echo
echo "=== extract BL tar.md5 ==="
rm -rf bl && mkdir -p bl
tar -xf BL_G970WVLU9IXE1_G970WVLU9IXE1_MQB80365760_REV00_user_low_ship_MULTI_CERT.tar.md5 -C bl 2>&1 | head -5
echo "=== contents ==="
ls -la bl
