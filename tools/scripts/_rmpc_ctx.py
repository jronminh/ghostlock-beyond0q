import subprocess, bisect
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
base=0x0b2eec; n=0x830
d=open(IMG,"rb").read()
open("/tmp/rmpc.bin","wb").write(d[base:base+n])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/rmpc.bin"],
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
    if i<0 or a-A[i]>0x400: return hex(a)
    return "%s+0x%x"%(syms[i][1], a-syms[i][0])
# print window around each rb_erase_cached call
targets=[0xb31f8,0xb3364,0xb340c]
for t in targets:
    print("=================== around %#x (%s) ===================" % (KIMAGE+t, nm(KIMAGE+t)))
    for l in out:
        try: a=int(l.split(":")[0].strip(),16)
        except: continue
        if KIMAGE+t-0x60 <= a <= KIMAGE+t+0x40:
            # annotate bl/b targets
            if "\tbl\t" in l or "\tb\t" in l:
                tt=l.split("\t")[-1].strip()
                try: l = l + "   ; " + nm(int(tt,16))
                except: pass
            print(l)
