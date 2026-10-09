import re, zipfile
CORE="/root/ghostlock/ghostlock-oneplus/src/core"
def show(fn, name, n=38):
    t=open(CORE+"/"+fn,errors="ignore").read().splitlines()
    for i,l in enumerate(t):
        if name in l and ("(" in l):
            print("--- %s @%s:%d ---" % (name, fn, i+1))
            for j in range(i, min(len(t), i+n)): print(t[j])
            return
    print("!! %s not found in %s" % (name, fn))

for fn,name in [("fops.c","open_ashmem_device"),("util.c","init_ashmem_path"),
                ("fops.c","configfs_write_once"),("fops.c","configfs_read_once")]:
    show(fn,name)

z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp85.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
print("\n=== boot memory lines ===")
for l in L[:3000]:
    if re.search(r"Memory:|memblock|0x80080000|0x80000000|Kernel code|Virtual kernel|reserve", l):
        print(l.split("]")[-1].strip()[:150])
