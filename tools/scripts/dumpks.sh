#!/bin/bash
cd ~/ghostlock || exit 1
echo "===== u32 @ 0x1d08d00 (nghi num_syms) ====="
python3 - <<'PY'
d=open('kernel/Image','rb').read()
import struct
for off in (0x1d08d00, 0x1d08d00+4, 0x1c806fc):
    print(hex(off), struct.unpack_from('<I', d, off)[0])
print("u64 @0x1d08cf8 =", hex(struct.unpack_from('<Q', d, 0x1d08cf8)[0]))
print("u64 @0x1d08ba0 =", hex(struct.unpack_from('<Q', d, 0x1d08ba0)[0]))
PY
echo
echo "===== region 0x1ed1300 (markers?) .. 0x1ed1900 ====="
xxd -s 0x1ed1300 -l 0x600 kernel/Image
