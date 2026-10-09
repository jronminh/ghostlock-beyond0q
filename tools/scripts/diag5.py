#!/usr/bin/env python3
import struct
data = open('kernel/Image','rb').read()
S_tt = 0x1ed2500; p_ti = 0x1ed28fa
def u16(o): return struct.unpack_from('<H', data, o)[0]
def token_len(s, lim):
    i = s
    while i < lim and data[i] != 0: i += 1
    return i - s
def tok(i):
    st = S_tt + u16(p_ti + 2*i)
    return data[st:st+token_len(st, p_ti)].decode('latin1', 'replace')
print("index[0..12] :", [u16(p_ti + 2*i) for i in range(13)])
print("index[248..256]:", [u16(p_ti + 2*i) for i in range(248, 256)])
print("token_table size =", p_ti - S_tt)
print("tokens[0..32]:", [tok(i) for i in range(32)])
print("tokens[250..]:", [tok(i) for i in range(250, 256)])
print("--- raw first name bytes @0x1d08e00 ---")
print(data[0x1d08e00:0x1d08e00+24].hex())
print("length byte =", data[0x1d08e00], " next tokens:", list(data[0x1d08e01:0x1d08e01+data[0x1d08e00]]))
