#!/bin/bash
# Bậc 1: AP archive -> boot.img -> kernel Image -> kallsyms -> offsets/feasibility
# Dùng: stage1_kernel.sh [đường-dẫn-AP-zip-hoặc-tar.md5]
set -e
cd ~/ghostlock || exit 1
G=/mnt/e/Library/Desktop/ghostlock
mkdir -p ap kernel

echo "#### 0. tìm AP ####"
SRC="$1"
if [ -z "$SRC" ] || [ ! -f "$SRC" ]; then
  SRC=$(ls -1 /mnt/e/Library/Desktop/AP_*.zip /mnt/e/Library/Desktop/AP_*.tar.md5 2>/dev/null | head -1)
fi
[ -n "$SRC" ] || { echo "Không thấy AP_*.zip / AP_*.tar.md5 trong E:\\Library\\Desktop"; exit 1; }
echo "AP source: $SRC"

echo "#### 1. unzip nếu cần ####"
case "$SRC" in
  *.zip) unzip -o "$SRC" -d ap >/dev/null; TAR=$(ls -1 ap/AP_*.tar.md5 ap/AP_*.tar 2>/dev/null | head -1) ;;
  *)     TAR="$SRC" ;;
esac
[ -n "$TAR" ] || { echo "Không thấy AP tar/md5 bên trong"; exit 1; }
echo "AP tar: $TAR"

echo "#### 2. giải nén boot.img ####"
tar -xf "$TAR" -C ap 2>/dev/null || true
BOOTLZ4=$(ls -1 ap/boot.img.lz4 2>/dev/null | head -1)
if [ -n "$BOOTLZ4" ]; then
  lz4 -d -f "$BOOTLZ4" ap/boot.img >/dev/null 2>&1
fi
[ -f ap/boot.img ] || { echo "Không có ap/boot.img"; ls -l ap; exit 1; }
ls -l ap/boot.img

echo "#### 3. bóc kernel Image ####"
python3 "$G/bootimg_extract.py" ap/boot.img kernel/Image

echo "#### 4. kallsyms ####"
if command -v vmlinux-to-elf >/dev/null 2>&1; then
  vmlinux-to-elf kernel/Image kernel/vmlinux.elf && ls -l kernel/vmlinux.elf
else
  echo "!! chưa có vmlinux-to-elf  ->  pip install vmlinux-to-elf"
fi

echo "#### 5. offset + feasibility ####"
if [ -f kernel/vmlinux.elf ]; then
  aarch64-linux-gnu-nm -n kernel/vmlinux.elf 2>/dev/null | awk '{print $1" "$2" "$3}' > kernel/kallsyms.txt
  wc -l kernel/kallsyms.txt
  python3 ghostlock-oneplus/tools/extract_target.py --kallsyms kernel/kallsyms.txt 2>&1 | head -60 || true
  python3 ghostlock-oneplus/tools/check_feasibility.py kernel/Image 2>&1 | head -80 || true
fi
echo "#### done ####"
