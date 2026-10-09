import subprocess
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
base=0x0b2eec; n=0x830
d=open(IMG,"rb").read()
open("/tmp/rmpc.bin","wb").write(d[base:base+n])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/rmpc.bin"],
                   capture_output=True,text=True).stdout.splitlines()
# find calls to rb_erase_cached (0xffffff80096e7a6c)
for i,l in enumerate(out):
    if "96e7a6c" in l or "rb_erase" in l:
        print(">>", l)
print("=== all bl/b targets ===")
seen={}
for l in out:
    if "\tbl\t" in l or "\tb\t" in l or "\ttbz" in l:
        t=l.split("\t")[-1].strip()
        seen[t]=seen.get(t,0)+1
for t,c in sorted(seen.items()):
    print("  %-40s x%d" % (t[:38], c))
