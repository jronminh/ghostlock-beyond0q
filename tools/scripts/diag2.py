#!/usr/bin/env python3
import struct
data = open('kernel/Image','rb').read()
names_start = 0x1d08e00
markers_start = 0x1ed1300
def u64(o): return struct.unpack_from('<Q', data, o)[0]
for off in (names_start-8, names_start-0x10, names_start-0x100, names_start-0x108, names_start-0x110):
    print("u64 @0x%x = %d" % (off, u64(off)))
pos = names_start; count = 0
while pos < markers_start:
    l = data[pos]
    if l == 0 or pos + 1 + l > markers_start:
        print("stop @0x%x (l=%d) after %d names" % (pos, l, count))
        break
    pos += 1 + l; count += 1
else:
    print("ended exactly at markers after %d names" % count)
print("bytes 0x1ed12c8..0x1ed1310:", data[0x1ed12c8:0x1ed1310].hex())
print("bytes 0x1d08d80..0x1d08e00 :", data[0x1d08d80:0x1d08e00].hex())
