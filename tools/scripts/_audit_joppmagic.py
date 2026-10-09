import struct
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
d=open(IMG,"rb").read()
targets={
 "ashmem_ioctl":0x1043F9C, "ashmem_compat_ioctl":0x10447F4, "ashmem_mmap":0x104484C,
 "ashmem_open":0x10449BC, "ashmem_release":0x1044A3C,
 "configfs_read_bin_file":0x2BE7DC, "configfs_write_bin_file":0x2BE96C,
 "generic_file_splice_read":0x24F2D4, "noop_llseek":0x20B474,
 "rb_erase_cached":0x16E7A6C, "el0_svc_naked":0x3BCC,
 "__arch_copy_to_user":0x16D9A80, "shmem_file_read_iter":0x1A9524,
}
print("check magic 0x00be7bad in the 4 bytes BEFORE each entry:")
for n,off in targets.items():
    pre=struct.unpack_from("<I", d, off-4)[0]
    print("  %-26s off=%#010x  pre=%#010x  %s" % (n, off, pre, "MAGIC OK" if pre==0x00be7bad else "no-magic"))
