#!/bin/bash
cd ~/ghostlock || exit 1
G=/mnt/e/Library/Desktop/ghostlock
Z='/mnt/e/Library/Desktop/SM-G970W_4_20240521161810_5uyevxvdd4_fac.zip'
AP='AP_G970WVLU9IXE1_G970WVLU9IXE1_MQB80365760_REV00_user_low_ship_MULTI_CERT_meta_OS12.tar.md5'
rm -rf ap kernel && mkdir -p ap kernel

echo "===== AP members (streamed, first 25) ====="
unzip -p "$Z" "$AP" 2>/dev/null | tar -tv 2>/dev/null | head -25

echo "===== extracting boot.img.lz4 (stop at first hit) ====="
unzip -p "$Z" "$AP" 2>/dev/null | tar -x --occurrence=1 -C ap boot.img.lz4 2>/dev/null
ls -la ap

if [ -f ap/boot.img.lz4 ]; then
  echo "===== lz4 -> boot.img ====="
  lz4 -d -f ap/boot.img.lz4 ap/boot.img
  ls -la ap/boot.img
  echo "===== boot.img -> kernel Image ====="
  python3 "$G/bootimg_extract.py" ap/boot.img kernel/Image
fi
