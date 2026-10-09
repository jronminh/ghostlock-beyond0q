import zipfile, re, sys
p=sys.argv[1] if len(sys.argv)>1 else "/mnt/e/Library/Desktop/ghostlock/kp87.gz"
z=zipfile.ZipFile(p)
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
idx=[i for i,l in enumerate(L) if "Unable to handle" in l or "Internal error" in l or "BUG:" in l]
print("fault points:", idx[:10])
for i in idx[:1]:
    for j in range(max(0,i-1), min(len(L), i+40)):
        print("%6d %s" % (j, L[j].split("]")[-1].strip()[:140]))
print("\n--- Call trace lines near fault ---")
for i in idx[:1]:
    for j in range(i, min(len(L), i+120)):
        if re.search(r"Call trace|^.* (pc|lr) :|Kernel panic|sec_debug_pm_restart| \w+\+0x", L[j]):
            print("%6d %s" % (j, L[j].split("]")[-1].strip()[:140]))
