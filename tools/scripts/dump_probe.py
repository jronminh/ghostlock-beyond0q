import struct, sys
d = open(sys.argv[1], 'rb').read()
names = ["sizeof(skb_shared_info)", "off.dataref", "off.frags", "off.destructor_arg",
         "sizeof(skb_frag_struct)", "sizeof(mm_struct)", "SMP_CACHE_BYTES"]
vals = [struct.unpack_from('<Q', d, i)[0] for i in range(0, len(d)//8*8, 8)]
for n, v in zip(names, vals):
    print("%-28s = 0x%x (%d)" % (n, v, v))
