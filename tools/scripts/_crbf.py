import subprocess
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
base=0x2be7dc; n=0x1e0   # read_bin_file then write_bin_file
d=open(IMG,"rb").read()
open("/tmp/crbf.bin","wb").write(d[base:base+n])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/crbf.bin"],
                   capture_output=True,text=True).stdout.splitlines()
for l in out[:60]:
    print(l)
