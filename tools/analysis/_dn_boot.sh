#!/bin/bash
cd "$HOME/ghostlock"
echo "=== file boot.img ==="
file ap/boot.img
echo "=== first bytes ==="
xxd -l 64 ap/boot.img
echo "=== search for ANDROID! and gzip/lz4 magics (offsets) ==="
python3 - <<'EOF'
import sys
d = open('/root/ghostlock/ap/boot.img','rb').read()
print("size", len(d), "hex", hex(len(d)))
for name, magic in [("ANDROID!", b"ANDROID!"), ("gzip", b"\x1f\x8b\x08"),
                    ("lz4-legacy", b"\x02\x21\x4c\x18"), ("lz4-frame", b"\x04\x22\x4d\x18"),
                    ("lzma", b"\x5d\x00\x00"), ("cpio-newc", b"070701"), ("cpio-odc", b"070707")]:
    offs = []
    i = d.find(magic)
    while i != -1 and len(offs) < 8:
        offs.append(hex(i)); i = d.find(magic, i+1)
    print("%-10s first offsets: %s" % (name, offs))
EOF
