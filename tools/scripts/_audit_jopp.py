def show(p, a, b, label):
    print("=== %s (%s:%d-%d) ===" % (label, p, a, b))
    L=open(p,errors="ignore").read().splitlines()
    for i in range(a-1, min(b, len(L))):
        print("%4d %s" % (i+1, L[i]))
show("/root/ghostlock/src/g9700/init/rkp_cfp.S", 1, 130, "rkp_cfp.S")
show("/root/ghostlock/src/g9700/include/linux/linkage.h", 90, 130, "linkage.h")
