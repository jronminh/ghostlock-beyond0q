#!/usr/bin/env python3
import struct
data = open('kernel/Image','rb').read()
def u16(o): return struct.unpack_from('<H', data, o)[0]
def tlen(s, lim):
    i = s
    while i < lim and data[i] != 0: i += 1
    return i - s
for p in (0x1ed2900, 0x1ed28fa, 0x1ed28fc, 0x1ed28fe):
    idx = [u16(p + 2*i) for i in range(256)]
    strict = all(idx[i] > idx[i-1] for i in range(1, 256))
    print("p=0x%x idx[:7]=%s idx255=%d strict=%s data[p-1]=%d" %
          (p, idx[:7], idx[255], strict, data[p-1]))
    if strict:
        tmax = idx[255]
        for delta in range(1, 40):
            S = p - tmax - delta
            good = True
            for i in range(256):
                st = S + idx[i]
                if st >= p or (i > 0 and data[st-1] != 0):
                    good = False; break
                L = tlen(st, p)
                nxt = p if i == 255 else S + idx[i+1]
                if L is None or st + L != nxt - 1:
                    good = False; break
            if good:
                print("   OK delta=%d S=0x%x size=%d" % (delta, S, p - S)); break
