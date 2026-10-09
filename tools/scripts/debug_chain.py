#!/usr/bin/env python3
import struct, sys
d = open(sys.argv[1], 'rb').read()
HDR = 256
auth = struct.unpack_from('>Q', d, 0x0C)[0]
aux = HDR + auth
p = aux
end = aux + struct.unpack_from('>Q', d, 0x68)[0]
while p < end:
    tag = struct.unpack_from('>Q', d, p)[0]
    nbf = struct.unpack_from('>Q', d, p + 8)[0]
    body = d[p + 16:p + 16 + nbf]
    if tag == 4:
        rloc, pn_len, pk_len = struct.unpack_from('>III', body, 0)
        name8 = body[8:8 + pn_len]
        name12 = body[12:12 + pn_len]
        print("CHAIN rloc=%d pn_len=%d pk_len=%d | body[0:20]=%s" %
              (rloc, pn_len, pk_len, body[:20].hex()))
        print("      name@8 =%r  name@12=%r" % (name8, name12))
    p += 16 + nbf
