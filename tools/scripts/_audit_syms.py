import struct, re
IMG="/root/ghostlock/kernel/Image"
KIMAGE=0xffffff8008000000
d=open(IMG,"rb").read()

# "ashmem" string and pointers to it
for s in (b"ashmem\x00", b"ashmem"):
    offs=[]; s0=0
    while True:
        i=d.find(s,s0)
        if i<0: break
        offs.append(i); s0=i+1
    print("string %r at image offsets:" % s, [hex(o) for o in offs[:10]])

ASHMEM_STR = 0x1a2d000  # placeholder, we'll print
# struct miscdevice at 0x2bb1750
base=0x2bb1750
print("\nmiscdevice @0x2bb1750 qwords:")
for k in range(0,0x60,8):
    v=struct.unpack_from("<Q",d,base+k)[0]
    print("  +%02x = %#018x" % (k,v))
# if .fops (+0x10) zero, maybe struct elsewhere: find qword == ashmem_fops in whole image
AF=KIMAGE+0x19cca30
pat=struct.pack("<Q",AF); r=[]; s0=0
while True:
    i=d.find(pat,s0)
    if i<0: break
    r.append(i); s0=i+1
print("\npointers to ashmem_fops (%#x):" % AF, [hex(o) for o in r[:10]], "total", len(r))
# find qword == KIMAGE+0x19cca30-relative? also try unslid .data.rel.ro style 0?
# print ashmem_fops table first qwords (rodata)
af=0x19cca30
print("\nashmem_fops @0x19cca30 qwords (off->value):")
for k in range(0,0x20,8):
    v=struct.unpack_from("<Q",d,af+k)[0]
    print("  +%02x = %#018x" % (k,v))

# configfs symbols
print("\nconfigfs / splice / llseek symbols in kallsyms_fixed:")
for line in open("/root/ghostlock/kernel/kallsyms_fixed.txt"):
    p=line.split()
    if len(p)>=3 and (("configfs" in p[2]) or ("splice_read" in p[2]) or ("noop_llseek" in p[2]) or ("selinux_enforcing" in p[2])):
        try: a=int(p[0],16)
        except: continue
        print("   %-40s off=%#010x" % (p[2], a-KIMAGE))
