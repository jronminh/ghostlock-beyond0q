#!/usr/bin/env python3
import struct
data = open('kernel/Image','rb').read()
def s32(o): return struct.unpack_from('<i', data, o)[0]
N = 139577
num_pos = 0x1d08d00
off_end = num_pos - 8
off_start = off_end - N*4
print("off_end=0x%x  computed off_start=0x%x" % (off_end, off_start))
print("first 8 :", [s32(off_start + 4*i) for i in range(8)])
print("last 4  :", [s32(off_end - 4*(4-i)) for i in range(4)])
print("first==0:", s32(off_start) == 0)
ok = all(s32(off_start + 4*i) <= s32(off_start + 4*(i+1)) for i in range(N-1))
print("sorted  :", ok)
print("--- compare tool anchor 0x1c806fc ---")
st2 = 0x1c806fc
print("first 8 :", [s32(st2 + 4*i) for i in range(8)])
print("(off_start - 0x1c806fc) =", off_start - 0x1c806fc)
