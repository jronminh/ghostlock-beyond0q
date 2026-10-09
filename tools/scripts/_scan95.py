import zipfile,re,sys
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp92.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
for i,l in enumerate(L):
    s=l.split("]")[-1].strip()
    if re.search(r"ghostlockT8|self-detected stall|sec_debug_pm_restart|Kernel Offset|Call trace|rt_mutex_adjust|configfs|mutex_lock|BUG:|watchdog", l):
        print("%6d %s" % (i, s[:130]))
