#!/usr/bin/env python3
data = open('kernel/Image','rb').read()
sym = {}
for line in open('kernel/kallsyms_fixed.txt'):
    p = line.split()
    if len(p) >= 3:
        sym[p[2]] = int(p[0], 16)
def at(off, n=48):
    return data[off:off+n]
for name in ('linux_banner','init_uts_ns','init_task','_etext','_sinittext','mk_seen_loaded'):
    o = sym.get(name)
    if o is None:
        print("%-16s NOT FOUND" % name); continue
    print("%-16s off=0x%x  bytes=%r" % (name, o, at(o, 40)))
# also: string 'Linux version' location in file
i = data.find(b'Linux version ')
print("file has 'Linux version' at 0x%x" % i)
