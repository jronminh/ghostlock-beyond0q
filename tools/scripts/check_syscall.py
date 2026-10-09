import struct
d = open('/root/ghostlock/kernel/Image', 'rb').read()
base = 0xffffff8008000000
tables = [('sys_call_table', 0xffffff8009781000),
          ('compat_sys_call_table', 0xffffff8009784000)]
want = {72: 'sys_pselect6', 1067: 'sys_select'}
for name, va in tables:
    for nr in (72, 1067):
        o = va - base + nr * 8
        v = struct.unpack_from('<Q', d, o)[0]
        print('%-22s nr=%-5d -> %#018x  (expect %s)' % (name, nr, v, want[nr]))
