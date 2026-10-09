import struct
d=open("/root/ghostlock/kernel/Image","rb").read(64)
print("code0=%08x code1=%08x" % struct.unpack_from("<II",d,0))
print("text_offset=0x%x" % struct.unpack_from("<Q",d,8)[0])
print("image_size=0x%x" % struct.unpack_from("<Q",d,16)[0])
print("flags=0x%x" % struct.unpack_from("<Q",d,24)[0])
print("res2=%s" % d[40:48].hex())
print("magic=%s" % d[56:60])
