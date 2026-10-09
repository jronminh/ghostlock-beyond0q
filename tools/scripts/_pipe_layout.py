import re
p="/root/ghostlock/src/g9700/include/linux/pipe_fs_i.h"
L=open(p,errors="ignore").read().splitlines()
for i,l in enumerate(L):
    if re.search(r"struct pipe_(buffer|inode_info)\s*\{", l):
        print("=== %s @%d ===" % (l.strip(), i+1))
        for j in range(i, min(len(L), i+34)): print("%4d %s"%(j+1,L[j]))
        print("---")
# exploit usage
import glob
print("=== exploit PIPE_* usage ===")
for fn in glob.glob("/root/ghostlock/ghostlock-oneplus/src/core/*.c"):
    for i,l in enumerate(open(fn,errors="ignore").read().splitlines(),1):
        if re.search(r"PIPE_(TMP_PAGE|BUFS|USER|HEAD|TAIL|RING_SIZE|BUF_FLAG|MAX_USAGE|INODE_INFO|BUFFER)", l):
            print("%s:%d: %s" % (fn.split("/")[-1], i, l.strip()[:130]))
