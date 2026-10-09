import zipfile
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp88.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
for j in range(18588, 18640):
    print("%6d %s" % (j, L[j].split("]")[-1].strip()[:150]))
