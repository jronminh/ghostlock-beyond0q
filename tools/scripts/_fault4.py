import zipfile, re, sys
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp88.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
for name in ("ghostlockT1","ghostlockSZ"):
    idx=[i for i,l in enumerate(L) if name in l]
    print("== %s: %d lines, first=%s last=%s" % (name, len(idx), idx[0] if idx else None, idx[-1] if idx else None))
# print faults with their process
for i,l in enumerate(L):
    if "Unable to handle kernel paging" in l:
        # process line within next 15
        proc="?"
        for j in range(i, min(len(L), i+20)):
            m=re.search(r"Process (\S+) \(pid: (\d+)", L[j])
            if m: proc=m.group(1)+":"+m.group(2); break
        print("fault@%d VA=%s proc=%s" % (i, l.split("address")[-1].strip()[:40], proc))
