import struct, re, sys
IMG="/root/ghostlock/kernel/Image"
KIMAGE=0xffffff8008000000
d=open(IMG,"rb").read()
print("Image size", hex(len(d)), "image_size hdr", hex(struct.unpack_from("<Q",d,16)[0]))

# --- 1) validate ashmem_misc.fops offset: Image[0x2bb1760] should be a pointer to ashmem_fops ---
ASHMEM_FOPS_IMG = KIMAGE + 0x19cca30
MISC_FOPS_OFF = 0x2bb1760
val = struct.unpack_from("<Q", d, MISC_FOPS_OFF)[0]
print("\n[1] Image[%#x] = %#x   (want ashmem_fops %#x)  %s" %
      (MISC_FOPS_OFF, val, ASHMEM_FOPS_IMG, "OK" if val==ASHMEM_FOPS_IMG else "MISMATCH"))

# where else does the value ashmem_fops appear in the image?
pat = struct.pack("<Q", ASHMEM_FOPS_IMG)
offs=[]
s=0
while True:
    i=d.find(pat, s)
    if i<0: break
    offs.append(i); s=i+1
print("[1b] ashmem_fops pointer found at image offsets:", [hex(o) for o in offs[:20]], "total", len(offs))

# --- 2) cross-check offsets.h _OFF values against kallsyms_fixed ---
syms={}
for line in open("/root/ghostlock/kernel/kallsyms_fixed.txt"):
    p=line.split()
    if len(p)>=3:
        try: a=int(p[0],16)
        except: continue
        syms[p[2]]=a
want = {
 "ashmem_misc":0x2bb1750, "ashmem_fops":0x19cca30,
 "ashmem_ioctl":0x1043F9C, "ashmem_mmap":0x104484C,
 "ashmem_open":0x10449BC, "ashmem_release":0x1044A3C,
 "configfs_read_iter":0x2BE7DC, "configfs_bin_write_iter":0x2BE96C,
 "copy_splice_read":0x24F2D4, "noop_llseek":0x20B474,
 "init_task":0x29A9780, "init_cred":0x220E0D0, "selinux_enforcing":0x2DC8CC8,
}
print("\n[2] kallsyms_fixed offset  vs  offsets.h")
for n,off in want.items():
    if n in syms:
        got=syms[n]-KIMAGE
        print("   %-22s kallsyms=%#010x  offsets.h=%#010x  %s" % (n, got, off, "OK" if got==off else "DIFF"))
    else:
        print("   %-22s (not in kallsyms_fixed)" % n)

# --- 3) byte patterns: verify a few by disasm-independent search ---
def find_words(ws):
    import struct as st
    pat=b"".join(st.pack("<I",w) for w in ws)
    r=[]; s=0
    while True:
        i=d.find(pat,s)
        if i<0: break
        r.append(i); s=i+1
    return r
print("\n[3] byte-pattern checks (Image file offset == kallsyms_fixed offset)")
print("   rb_erase_cached prologue at", [hex(x) for x in find_words([0xa940a009,0xb100202a,0x54000080,0xf940014b,0xeb00017f,0x54000280,0xb4000a88,0xb40002e9])][:5])
print("   _raw_spin_trylock prologue candidates:", [hex(x) for x in find_words([0x885ffc09])][:8], "(>=1 match; check against", hex(0x16f99c4),")")
