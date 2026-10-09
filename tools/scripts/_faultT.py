import zipfile,re,sys
p=sys.argv[1] if len(sys.argv)>1 else "/mnt/e/Library/Desktop/ghostlock/kpT14.gz"
z=zipfile.ZipFile(p)
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
idx=[i for i,l in enumerate(L) if "Unable to handle kernel paging" in l or "Internal error" in l]
print("faults:", idx[:8])
for i in idx[-1:]:
    for j in range(i-1, min(len(L), i+24)):
        print("%6d %s" % (j, L[j].split("]")[-1].strip()[:140]))
print("=== collect_rr panic msg ===")
for i,l in enumerate(L):
    if "panic_msg" in l or ("sec_debug_pm_restart" in l and "rebooting" in l):
        print("%6d %s" % (i, l.split("]")[-1].strip()[:150]))
