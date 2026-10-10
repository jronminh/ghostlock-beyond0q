#!/bin/bash
echo "==SDK=="
find /root/ghostlock/src/orig/android-sdk -maxdepth 5 -iname '*clang*' 2>/dev/null | head
ls /root/ghostlock/src/orig/android-sdk 2>&1 | head
echo "==CLONE=="
cd /root/ghostlock || exit 1
rm -rf _ksu
for u in \
  https://github.com/ReSukiSU/ReSukiSU.git \
  https://github.com/SukiSU-Ultra/SukiSU-Ultra.git \
  https://github.com/ShirkNeko/SukiSU-Ultra.git ; do
  echo "TRY $u"
  timeout 240 git clone --depth 1 "$u" _ksu 2>&1 | tail -2
  if [ -d _ksu/.git ]; then echo CLONED; break; fi
  rm -rf _ksu
done
echo "==RESULT=="
ls _ksu 2>&1 | head
