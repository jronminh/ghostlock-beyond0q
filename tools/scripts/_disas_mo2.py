import subprocess
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
base=0x869ee9c
d=open(IMG,"rb").read()
open("/tmp/mo.bin","wb").write(d[base:base+0x178])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/mo.bin"],
                   capture_output=True,text=True).stdout
print(out)
