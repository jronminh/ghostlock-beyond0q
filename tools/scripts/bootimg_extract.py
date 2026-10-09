#!/usr/bin/env python3
"""Extract + decompress the kernel from an Android boot.img (v0/v1/v2)."""
import struct, sys, subprocess

MAGICS = [
    (b'\x1f\x8b', 'gzip'),
    (b'\x04\x22\x4d\x18', 'lz4'),
    (b'\x02\x21\x4c\x18', 'lz4legacy'),
    (b'\xfd\x37\x7a\x58\x5a\x00', 'xz'),
    (b'\x28\xb5\x2f\xfd', 'zstd'),
    (b'\x5d\x00\x00', 'lzma'),
]

def decomp(cmd, data):
    p = subprocess.run(cmd, input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return p.stdout

def decompress(payload):
    if payload[0x38:0x3c] == b'ARM\x64':
        return payload, 'raw(arm64 Image)'
    for m, name in MAGICS:
        if payload.startswith(m):
            if name == 'gzip':
                return decomp(['gzip', '-dc'], payload), 'gzip'
            if name == 'lz4':
                return decomp(['lz4', '-dc'], payload), 'lz4'
            if name == 'lz4legacy':
                return decomp(['lz4', '-dc', '-l'], payload), 'lz4-legacy'
            if name == 'xz':
                return decomp(['xz', '-dc'], payload), 'xz'
            if name == 'zstd':
                return decomp(['zstd', '-dc'], payload), 'zstd'
            if name == 'lzma':
                return decomp(['xz', '-dc', '--format=lzma'], payload), 'lzma'
    idx = payload.find(b'ARM\x64')
    if idx >= 0x38:
        return payload[idx-0x38:], 'raw(arm64 Image, scanned @0x%x)' % (idx-0x38)
    return payload, 'unknown'

def main():
    src, out = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    assert d[:8] == b'ANDROID!', 'not a boot image: %r' % d[:8]
    kernel_size = struct.unpack_from('<I', d, 8)[0]
    page_size = struct.unpack_from('<I', d, 36)[0] or 2048
    payload = d[page_size:page_size+kernel_size]
    data, how = decompress(payload)
    open(out, 'wb').write(data)
    print("boot.img             : %d bytes, page=%d, kernel_size=%d" % (len(d), page_size, kernel_size))
    print("kernel Image         : %d bytes  (%s)" % (len(data), how))
    print("arm64 magic @0x38    : %r  (expect b'ARM\\x64')" % data[0x38:0x3c])
    i = data.find(b'Linux version ')
    if i >= 0:
        print("banner               : %s" % data[i:i+140].split(b'\x00')[0].decode('ascii', 'replace'))
    else:
        print("banner               : NOT FOUND (kernel may still be compressed)")

if __name__ == '__main__':
    main()
