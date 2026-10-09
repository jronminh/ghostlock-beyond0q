import subprocess, bisect
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
base=0x2be96c; n=0x120
d=open(IMG,"rb").read()
open("/tmp/cwbf.bin","wb").write(d[base:base+n])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/cwbf.bin"],
                   capture_output=True,text=True).stdout.splitlines()
syms=[]
for line in open("/root/ghostlock/kernel/kallsyms_fixed.txt"):
    p=line.split()
    if len(p)>=3:
        try: a=int(p[0],16)
        except: continue
        syms.append((a,p[2]))
syms.sort(); A=[s[0] for s in syms]
def nm(a):
    i=bisect.bisect_right(A,a)-1
    return "%s+0x%x"%(syms[i][1], a-syms[i][0]) if 0<=i and a-A[i]<0x800 else hex(a)
for l in out:
    if "\tbl\t" in l:
        try: l=l+"   ; "+nm(int(l.split("\t")[-1].strip(),16))
        except: pass
    print(l)
