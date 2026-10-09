import struct
d = open('/root/ghostlock/ap/boot.img', 'rb').read(4096)
print('magic   =', d[0:8])
if d[0:8] == b'ANDROID!':
    ks, ka, rs, ra, ss, sa = struct.unpack_from('<6I', d, 8)
    tags, page, dt, unused = struct.unpack_from('<4I', d, 8+24)
    print('kernel_size =', hex(ks))
    print('kernel_addr =', hex(ka))
    print('ramdisk_addr=', hex(ra))
    print('second_addr =', hex(sa))
    print('tags_addr   =', hex(tags))
    print('page_size   =', hex(page))
    print('dt_size     =', hex(dt))
    print('name        =', d[48:64])
    print('cmdline     =', d[64:64+512].split(b'\0')[0])
else:
    print('not ANDROID! ; first 64 bytes:', d[:64])
    # samsung may prefix; search for magic
    i = d.find(b'ANDROID!')
    print('ANDROID! at', i)
