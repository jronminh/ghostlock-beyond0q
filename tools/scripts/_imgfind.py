#!/usr/bin/env python3
"""_imgfind.py — tim chuoi byte trong Image, tra offset/kallsyms."""
import sys
IMG = "/root/ghostlock/kernel/Image"
data = open(IMG, "rb").read()
print("Image size", hex(len(data)))

# rb_erase_cached start (from kppc ghostlockPC dump, window line "7a6c")
# words: a940a009 b100202a 54000080 f940014b eb00017f 54000280 b4000a88 b40002e9
import struct
words = [0xa940a009,0xb100202a,0x54000080,0xf940014b,0xeb00017f,0x54000280,0xb4000a88,0xb40002e9]
pat = b"".join(struct.pack("<I", w) for w in words)
print("pattern", pat.hex())
idxs = []
start = 0
while True:
    i = data.find(pat, start)
    if i < 0: break
    idxs.append(i)
    start = i + 1
print("hits:", [hex(i) for i in idxs])
KIMAGE = 0xffffff8008000000
FIXED_RBE = 0xffffff80096e7a6c  # kallsyms_fixed
for i in idxs:
    # hypothesize file offset i corresponds to some vaddr v = KIMAGE + i
    print("  off=%#x  as_vaddr=KIMAGE+off=%#x  (kallsyms_fixed=%#x, diff=%+#x)" %
          (i, KIMAGE + i, FIXED_RBE, (KIMAGE + i) - FIXED_RBE))
