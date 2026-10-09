import struct
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
d=open(IMG,"rb").read()

def find(s, n=15):
    r=[]; s0=0
    while True:
        i=d.find(s,s0)
        if i<0: break
        r.append(i); s0=i+1
    return r[:n]

# 1) init_task.comm via "swapper/0"
sw=find(b"swapper/0")
print("'swapper/0' image offsets:", [hex(x) for x in sw])
# beyond0q: task_comm=0x858 ; oneplus target.h TASK_COMM_OFF=0x910
for comm in (0x858, 0x910):
    for s in sw:
        print("   if comm_off=%#x -> init_task img off = %#x (kallsyms says 0x29a9780)" % (comm, s-comm))

# 2) pointers to the "ashmem" string (all candidates)
for so in find(b"ashmem\x00"):
    v=KIMAGE+so
    pat=struct.pack("<Q",v)
    r=find(pat,10)
    print("&'ashmem'=%#x -> pointer found at:" % v, [hex(x) for x in r])

# 3) sanity: pointer to init_task? often stored in .data
v=KIMAGE+0x29a9780; pat=struct.pack("<Q",v); r=find(pat,10)
print("&init_task pointers at:", [hex(x) for x in r])

# 4) where is 'ashmem' string relative to .rodata symbols? check generic_file_splice_read region not needed.
# 5) dump miscdevice-shaped structs: find qwords == &'ashmem'
