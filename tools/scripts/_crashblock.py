import zipfile, re, sys
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp86.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
pid=sys.argv[1] if len(sys.argv)>1 else "12904"
idx=[i for i,l in enumerate(L) if pid in l]
print("lines with pid %s: %d, first=%s last=%s" % (pid,len(idx),idx[0] if idx else None,idx[-1] if idx else None))
# print the first crash-ish region
for i in idx[:1]:
    lo=max(0,i-3)
    for j in range(lo, min(len(L), lo+120)):
        print("%6d %s" % (j, L[j].split("]")[-1].strip()[:130]))
