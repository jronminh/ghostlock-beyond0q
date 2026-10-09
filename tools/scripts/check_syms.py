import struct
d = open('/root/ghostlock/kernel/Image', 'rb').read()
base = 0xffffff8008000000
def show(tag, va, n=48):
    off = va - base
    print('%-16s va=%#x off=%#x %r' % (tag, va, off, d[off:off+n]))
show('linux_banner', 0xffffff800978000f)
show('sys_call_table', 0xffffff8009781000)
# sys_call_table[72] and [1067]
for nr in (72, 1067):
    off = 0xffffff8009781000 - base + nr*8
    print('entry', nr, '=', hex(struct.unpack_from('<Q', d, off)[0]))
