#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
# make stdout unbuffered so the last line survives a panic
if ! grep -q 'setvbuf(stdout' src/core/main.c; then
  sed -i 's#^int main(int argc, char \*\*argv) {#int main(int argc, char **argv) {\n    setvbuf(stdout, NULL, _IONBF, 0);#' src/core/main.c
fi
grep -n 'setvbuf' src/core/main.c
echo "=== rebuild ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -Isrc/core -Isrc/devices \
  -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock3 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock3 /mnt/e/Library/Desktop/ghostlock/ghostlock3_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock3_a64
