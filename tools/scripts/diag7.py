#!/usr/bin/env python3
import struct
data = open('kernel/Image','rb').read()
def u16(o): return struct.unpack_from('<H', data, o)[0]
def tlen(s, lim):
    i = s
    while i < lim and data[i] != 0: i += 1
    return i - s
p = 0x1ed2900; S = 0x1ed2500
idx = [u16(p + 2*i) for i in range(256)]
ok = True
for i in range(255):
    st = S + idx[i]
    if i > 0 and data[st-1] != 0:
        print("fail prevnull at i=%d st=0x%x" % (i, st)); ok = False; break
    L = tlen(st, p)
    if L != idx[i+1] - idx[i] - 1:
        print("fail len i=%d L=%d exp=%d tok=%r" % (i, L, idx[i+1]-idx[i]-1, data[st:st+L])); ok = False; break
print("first 255 packed:", ok)
st = S + idx[255]
print("idx255=%d  token255 start=0x%x  tlen=%d  bytes=%r" % (idx[255], st, tlen(st, p), data[st:st+16]))
print("S+idx255=%d  p-S=%d" % (idx[255], p - S))
