import struct, subprocess
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
syms={}
for line in open("/root/ghostlock/kernel/kallsyms_fixed.txt"):
    p=line.split()
    if len(p)>=3:
        try: a=int(p[0],16)
        except: continue
        syms[p[2]]=a-KIMAGE
print("misc_open off=%#x try_module_get off=%#x" % (syms["misc_open"], syms.get("try_module_get",0)))
d=open(IMG,"rb").read()
base=syms["misc_open"]; n=0x178
open("/tmp/miscopen.bin","wb").write(d[base:base+n])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/miscopen.bin"],
                   capture_output=True,text=True).stdout.splitlines()
for l in out:
    print(l)
