import subprocess, os
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
base=0x69ee9c
d=open(IMG,"rb").read()
open("/tmp/mo.bin","wb").write(d[base:base+0x178])
print("mo.bin size", os.path.getsize("/tmp/mo.bin"))
r=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                  "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/mo.bin"],
                 capture_output=True,text=True)
print("rc", r.returncode)
print("STDOUT len", len(r.stdout))
print("STDERR", r.stderr[:500])
print(r.stdout[:4000])
