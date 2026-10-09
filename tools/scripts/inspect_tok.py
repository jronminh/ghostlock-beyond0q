#!/usr/bin/env python3
import struct
data = open('kernel/Image','rb').read()
p_ti = 0x17e2290; S = 0x17e1a87
def u16(o): return struct.unpack_from('<H', data, o)[0]
def tok(i):
    st = S + u16(p_ti + 2*i); en = st
    while data[en] != 0: en += 1
    return data[st:en].decode('latin1')
print("index[0..12] :", [u16(p_ti+2*i) for i in range(13)])
print("tokens[0..30]:", [tok(i) for i in range(30)])
print("tokens[240..256]:", [tok(i) for i in range(240,256)])
print("S+size=0x%x  p_ti=0x%x" % (S+2057, p_ti))
print("--- 96 bytes before token_table ---")
print(data[S-96:S])
print("--- 48 bytes after token_index ---")
print(data[p_ti+512:p_ti+512+48])
print("--- hexdump 0x17e1a00..0x17e1a90 ---")
print(data[0x17e1a00:0x17e1a90].hex())
