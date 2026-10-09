import zipfile
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp92.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
idx=[i for i,l in enumerate(L) if "Unable to handle kernel paging" in l]
print("faults:", idx)
for i in idx[-1:]:
    for j in range(i-1, min(len(L), i+26)):
        print("%6d %s" % (j, L[j].split("]")[-1].strip()[:140]))
