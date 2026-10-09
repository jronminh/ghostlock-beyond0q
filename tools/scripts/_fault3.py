import zipfile, re, sys
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp87.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
idx=[i for i,l in enumerate(L) if "Unable to handle kernel paging" in l]
i=idx[-1]
for j in range(max(0,i-1), min(len(L), i+50)):
    print("%6d %s" % (j, L[j].split("]")[-1].strip()[:150]))
