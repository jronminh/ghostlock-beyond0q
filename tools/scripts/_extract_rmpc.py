import subprocess, struct, os
IMG="/root/ghostlock/kernel/Image"
KIMAGE=0xffffff8008000000
# rt_mutex_adjust_prio_chain kallsyms_fixed addr
BASE=0xffffff80080b2eec
start=BASE-KIMAGE          # == file offset
n=0x830
data=open(IMG,"rb").read()[start:start+n]
open("/tmp/rmpc.bin","wb").write(data)
print("wrote /tmp/rmpc.bin len", len(data), "start off", hex(start))
