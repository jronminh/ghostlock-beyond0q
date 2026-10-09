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
    st = S_tt + u16(p_ti + 2*i); return data[st:st+tlen(st, p_ti)].decode('latin1')
pos = names_start; names = []
while pos < markers_start:
    l = data[pos]
    if l == 0 or pos + 1 + l > markers_start: break
    q = pos + 1; s = []
    for k in range(l):
        s.append(tok(data[q])); q += 1
    names.append(''.join(s)[1:]); pos = q
N = len(names)
off_start = 0x1c80700
offs = [s32(off_start + 4*i) for i in range(N)]
print("sorted:", all(offs[i] <= offs[i+1] for i in range(N-1)), " first:", offs[0], " last:", offs[-1])
idx = {n: i for i, n in enumerate(names)}
for want in ('linux_banner','do_futex','core_sys_select','futex_wait','_etext','init_task'):
    i = idx.get(want)
    print("  %-18s idx=%-6s off=0x%x" % (want, i, offs[i] if i is not None else -1))
lb = offs[idx['linux_banner']]
print("bytes at linux_banner: %r" % data[lb:lb+24])
