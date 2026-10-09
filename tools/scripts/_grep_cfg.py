import re,glob,os
CORE="/root/ghostlock/ghostlock-oneplus/src/core"
pat=re.compile(r"configfs_write_once|configfs_read_once|binwrite_target|kernel_write_data|kernel_read64")
for fn in glob.glob(CORE+"/*.c")+glob.glob(CORE+"/*.h"):
    for i,l in enumerate(open(fn,errors="ignore").read().splitlines(),1):
        if pat.search(l):
            print("%s:%d: %s" % (os.path.basename(fn), i, l.strip()[:140]))
