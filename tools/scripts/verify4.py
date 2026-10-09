#!/usr/bin/env python3
import struct
data = open('kernel/Image','rb').read()
S_tt = 0x1ed2500; p_ti = 0x1ed2900; names_start = 0x1d08e00; markers_start = 0x1ed1300
def u16(o): return struct.unpack_from('<H', data, o)[0]
def s32(o): return struct.unpack_from('<i', data, o)[0]
def tlen(s, lim):
    i = s
    while i < lim and data[i] != 0: i += 1
    return i - s
def tok(i):
    st = S_tt + u16(p_ti + 2*i)
    return data[st:st+tlen(st, p_ti)].decode('latin1')

pos = names_start; names = []
while pos < markers_start:
    l = data[pos]
    if l == 0 or pos + 1 + l > markers_start: break
    q = pos + 1; s = []
    for k in range(l):
        s.append(tok(data[q])); q += 1
    names.append(''.join(s)[1:]); pos = q
N = len(names)
k_lb = names.index('linux_banner')
print("N=%d  linux_banner idx=%d  names[idx-1..idx+1]=%s" %
      (N, k_lb, names[k_lb-1:k_lb+2]))
# file offset of "Linux version" string
lb_off = data.find(b'Linux version ')
print("'Linux version' file off = 0x%x" % lb_off)
# find position of a 4-byte value ~ lb_off in candidate region
hits = []
for p in range(0x1c00000, 0x1d10000, 4):
    v = s32(p)
    if abs(v - lb_off) < 0x4000:
        hits.append((p, v))
print("candidate value hits:", [(hex(p), hex(v)) for p, v in hits])
for p, v in hits:
    X = p - 4*k_lb
    print("  -> implied off_start=0x%x  check s32(X)=%d sorted_head=%s" %
          (X, s32(X), [s32(X+4*i) for i in range(4)]))
