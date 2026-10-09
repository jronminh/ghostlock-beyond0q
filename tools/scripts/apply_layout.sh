#!/bin/bash
cd ~/ghostlock/ghostlock-oneplus || exit 1
python3 - <<'PY'
p='src/core/target.h'
s=open(p).read()
rep = {
 '#define KIMAGE_TEXT_BASE 0xffffffc080000000ULL':'#define KIMAGE_TEXT_BASE 0xffffff8008000000ULL',
 '#define P0_PAGE_OFFSET 0xffffff8000000000ULL':'#define P0_PAGE_OFFSET 0xffffffc000000000ULL',
 '#define KERNELSNITCH_IDENTITY_START 0xffffff8000000000ULL':'#define KERNELSNITCH_IDENTITY_START 0xffffffc000000000ULL',
 '#define KERNELSNITCH_IDENTITY_END   0xffffff8c00000000ULL':'#define KERNELSNITCH_IDENTITY_END   0xffffffc400000000ULL',
 '#define DIRECT_MAP_BASE 0xffffff8000000000ULL':'#define DIRECT_MAP_BASE 0xffffffc000000000ULL',
 '#define DIRECT_MAP_END 0xffffff9000000000ULL':'#define DIRECT_MAP_END 0x0ULL',
 '#define VMEMMAP_START 0xfffffffe00000000ULL':'#define VMEMMAP_START 0xffffffbf00000000ULL',
}
n=0
for a,b in rep.items():
    if a in s: s=s.replace(a,b); n+=1
    else: print("MISS:",a)
open(p,'w').write(s)
print("replaced",n,"of",len(rep))
PY
grep -nE 'KIMAGE_TEXT_BASE |P0_PAGE_OFFSET|IDENTITY_START|IDENTITY_END|DIRECT_MAP_|VMEMMAP_START' src/core/target.h | head
echo "=== rebuild ==="
SRC="src/core/main.c src/core/util.c src/core/slide.c src/core/fops.c src/core/pipe_physrw.c src/core/root.c src/core/miniadb.c src/core/umh_root.c"
aarch64-linux-gnu-gcc -O2 -w -include stddef.h -DKERNELSNITCH_THRESHOLD_MULT=30 \
  -Isrc/core -Isrc/devices -DTARGET_CONFIG_H='"target.h"' $SRC -o /tmp/ghostlock8 -static -pthread 2>&1 | grep -iE 'error' | head
cp -f /tmp/ghostlock8 /mnt/e/Library/Desktop/ghostlock/ghostlock8_a64
ls -la /mnt/e/Library/Desktop/ghostlock/ghostlock8_a64
