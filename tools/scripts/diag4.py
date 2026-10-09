#!/usr/bin/env python3
import struct, array
data = open('kernel/Image','rb').read()
S_tt = 0x1ed2500; p_ti = 0x1ed28fa
names_start = 0x1d08e00; markers_start = 0x1ed1300
num_pos = 0x1d08d00; N = 139577

def u16(o): return struct.unpack_from('<H', data, o)[0]
def s32(o): return struct.unpack_from('<i', data, o)[0]

def tok(i):
    st = S_tt + u16(p_ti + 2*i)
    en = st
    while data[en] != 0: en += 1
    return data[st:en].decode('latin1')

pos = names_start; names = []
while pos < markers_start:
    l = data[pos]
    if l == 0 or pos + 1 + l > markers_start:
        break
    q = pos + 1; s = []
    for k in range(l):
        s.append(tok(data[q])); q += 1
    full = ''.join(s); names.append((full[1:], full[0])); pos = q
print("names decoded:", len(names), " first:", names[0], " last:", names[-1][0])

s32arr = array.array('i'); s32arr.frombytes(data[: (len(data)//4)*4])
base_guess = num_pos - N*4
print("base_guess=0x%x" % base_guess)
found = None
for st in range(base_guess - 0x2000, base_guess + 0x2000, 4):
    if st < 0 or st % 4: continue
    if s32arr[st//4] != 0: continue
    prev = 0; ok = True
    for i in range(1, N):
        v = s32arr[st//4 + i]
        if v < prev: ok = False; break
        prev = v
    if ok:
        found = (st, prev); break
if not found:
    print("no sorted zero-based run found near base_guess")
else:
    st, last = found
    print("OFFSETS start=0x%x  last=0x%x (%d)" % (st, last, last))
    for want in ('do_futex','core_sys_select','init_task','_text'):
        idx = next((i for i,(nm,t) in enumerate(names) if nm == want), None)
        print("   %-18s idx=%s off=0x%x" % (want, idx, s32arr[st//4+idx] if idx is not None else -1))
