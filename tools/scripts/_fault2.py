import zipfile, re, sys
p=sys.argv[1]
z=zipfile.ZipFile(p)
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
proc=sys.argv[2] if len(sys.argv)>2 else "ghostlockSZ"
idx=[i for i,l in enumerate(L) if re.search(r"Unable to handle kernel paging", l)]
print("real faults:", idx[:10])
if idx:
    i=idx[0]
    for j in range(max(0,i-2), min(len(L), i+55)):
        print("%6d %s" % (j, L[j].split("]")[-1].strip()[:150]))
