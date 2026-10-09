#!/usr/bin/env python3
# AVB vbmeta parser (header + descriptor fields are BIG-ENDIAN)
import struct, sys, hashlib

path = sys.argv[1]
d = open(path, 'rb').read()
assert d[:4] == b'AVB0', "not AVB0: %r" % d[:4]

HDR = 256  # AVB_VBMETA_IMAGE_HEADER_SIZE
BE = '>'

def u32(off): return struct.unpack_from(BE+'I', d, off)[0]
def u64(off): return struct.unpack_from(BE+'Q', d, off)[0]

maj = u32(4); minor = u32(8)
auth_size = u64(0x0C)
aux_size  = u64(0x14)
alg       = u32(0x1C)
hash_off  = u64(0x20); hash_size = u64(0x28)
sig_off   = u64(0x30); sig_size  = u64(0x38)
pk_off    = u64(0x40); pk_size   = u64(0x48)
pkm_off   = u64(0x50); pkm_size  = u64(0x58)
desc_off  = u64(0x60); desc_size = u64(0x68)
rollback  = u64(0x70)
flags     = u32(0x78)
rb_loc    = u32(0x7C)
rel = d[0x80:0x80+48].split(b'\0')[0].decode('ascii','replace')
num_desc = u32(0x100)
hdr_chk  = u32(0x104)

ALG = {0:"NONE",1:"SHA256_RSA2048",2:"SHA256_RSA4096",3:"SHA256_RSA8192",
       4:"SHA512_RSA2048",5:"SHA512_RSA4096",6:"SHA512_RSA8192"}

print("libavb        : %d.%d" % (maj, minor))
print("algorithm     : %s" % ALG.get(alg, alg))
print("flags         : 0x%x%s%s" % (flags,
      " [hashtree_disabled]" if flags & 1 else "",
      " [verification_disabled]" if flags & 2 else ""))
print("rollback_index: %d (loc %d)" % (rollback, rb_loc))
print("release_string: %s" % rel)
print("auth_block=%d aux_block=%d  hash=%d sig=%d pubkey=%d" %
      (auth_size, aux_size, hash_size, sig_size, pk_size))
print("num_descriptors: %d" % num_desc)
print("pubkey sha256 : %s" % hashlib.sha256(d[HDR+auth_size+pk_off:HDR+auth_size+pk_off+pk_size]).hexdigest())
print("---- descriptors ----")

aux = HDR + auth_size
p = aux + desc_off
end = p + desc_size
while p < end:
    tag = u64(p); nbf = u64(p+8); p += 16
    body = d[p:p+nbf]; p += nbf
    if tag == 0:  # property
        klen = u64(0) if False else struct.unpack_from(BE+'Q', body, 0)[0]
        vlen = struct.unpack_from(BE+'Q', body, 8)[0]
        key = body[16:16+klen].split(b'\0')[0].decode('ascii','replace')
        val = body[16+klen:16+klen+vlen].split(b'\0')[0]
        print("PROP  %-40s = %s" % (key, val.decode('ascii','replace')))
    elif tag == 1:  # hash descriptor
        image_size = struct.unpack_from(BE+'Q', body, 0)[0]
        hash_alg   = struct.unpack_from(BE+'I', body, 8)[0]
        pn_len     = struct.unpack_from(BE+'I', body, 12)[0]
        salt_len   = struct.unpack_from(BE+'I', body, 16)[0]
        dig_len    = struct.unpack_from(BE+'I', body, 20)[0]
        df         = struct.unpack_from(BE+'I', body, 24)[0]
        name = body[28:28+pn_len].split(b'\0')[0].decode('ascii','replace')
        print("HASH  %-14s size=%-11d alg=%d flags=0x%x %s" %
              (name, image_size, hash_alg, df,
               "NOENFORCE" if (df & 1) else "ENFORCE"))
    elif tag == 2:  # hashtree
        dmv = struct.unpack_from(BE+'I', body, 0)[0]
        image_size = struct.unpack_from(BE+'Q', body, 4)[0]
        tree_off   = struct.unpack_from(BE+'Q', body, 12)[0]
        tree_size  = struct.unpack_from(BE+'Q', body, 20)[0]
        data_bs    = struct.unpack_from(BE+'I', body, 28)[0]
        hash_bs    = struct.unpack_from(BE+'I', body, 32)[0]
        hash_alg   = struct.unpack_from(BE+'I', body, 36)[0]
        pn_len     = struct.unpack_from(BE+'I', body, 48)[0]
        name = body[60:60+pn_len].split(b'\0')[0].decode('ascii','replace')
        print("TREE  %-14s img=%-11d data_bs=%d hash_bs=%d alg=%d tree_off=%d" %
              (name, image_size, data_bs, hash_bs, hash_alg, tree_off))
    elif tag == 3:  # kernel cmdline descriptor
        cflags = struct.unpack_from(BE+'I', body, 0)[0]
        clen   = struct.unpack_from(BE+'I', body, 4)[0]
        cmd = body[8:8+clen].split(b'\0')[0].decode('ascii','replace')
        print("CMDLINE flags=0x%x : %s" % (cflags, cmd[:200]))
    elif tag == 4:  # chain partition
        rloc   = struct.unpack_from(BE+'I', body, 0)[0]
        pn_len = struct.unpack_from(BE+'I', body, 4)[0]
        pk_len = struct.unpack_from(BE+'I', body, 8)[0]
        name = body[12:12+pn_len].split(b'\0')[0].decode('ascii','replace')
        print("CHAIN %-16s rollback_loc=%-3d pubkey_len=%d" % (name, rloc, pk_len))
    else:
        print("DESC  tag=%d len=%d" % (tag, nbf))
