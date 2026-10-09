import re
CORE="/root/ghostlock/ghostlock-oneplus/src/core"
def show(fn,name,n=30):
    L=open(CORE+"/"+fn,errors="ignore").read().splitlines()
    for i,l in enumerate(L):
        if re.search(r"\b"+name+r"\s*\(", l) and "{" not in l and l.rstrip().endswith(")"):
            for j in range(i, min(len(L), i+n)): print("%4d %s"%(j+1,L[j]))
            return
    print("not found", name)
show("fops.c","open_ashmem_device", 26)
