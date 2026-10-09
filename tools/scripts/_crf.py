import subprocess
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
base=0x2be46c; n=0x130
d=open(IMG,"rb").read()
open("/tmp/crf.bin","wb").write(d[base:base+n])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/crf.bin"],
                   capture_output=True,text=True).stdout.splitlines()
for l in out[:36]:
    print(l)
