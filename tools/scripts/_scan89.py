import zipfile,re
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp89.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
for i,l in enumerate(L):
    s=l.split("]")[-1].strip()
    if ("ghostlockT2" in l) or ("Unable to handle" in l) or ("self-detected stall" in l) or ("sec_debug_pm_restart" in l) or ("Kernel Offset" in l):
        print("%6d %s" % (i, s[:140]))
