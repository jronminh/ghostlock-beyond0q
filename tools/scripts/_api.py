import subprocess,bisect
IMG="/root/ghostlock/kernel/Image"; KIMAGE=0xffffff8008000000
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
    return "%s+0x%x"%(syms[i][1],a-syms[i][0]) if 0<=i and a-A[i]<0x800 else hex(a)
for name in ("alloc_pipe_info","pipe_write","pipe_read","anon_pipe_buf_ops","init_pipe_fs"):
    for a,n in syms:
        if n==name:
            print("%s = %#x (off %#x)" % (name,a,a-KIMAGE)); break
# disasm alloc_pipe_info
base=None
for a,n in syms:
    if n=="alloc_pipe_info": base=a-KIMAGE; break
d=open(IMG,"rb").read()
open("/tmp/api.bin","wb").write(d[base:base+0x260])
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0x%x"%(KIMAGE+base),"/tmp/api.bin"],capture_output=True,text=True).stdout
for l in out.splitlines():
    if "\tbl\t" in l:
        try: l=l+"  ; "+nm(int(l.split("\t")[-1].strip(),16))
        except: pass
    if ("str" in l and ("[x19" in l or "[x20" in l or "[x21" in l)) or "\tbl\t" in l or "mov\tx19" in l:
        print(l)
