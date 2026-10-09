import re,glob,os
CORE="/root/ghostlock/ghostlock-oneplus/src/core"
for fn in sorted(glob.glob(CORE+"/*.c")+glob.glob(CORE+"/*.h")):
    for i,l in enumerate(open(fn,errors="ignore").read().splitlines(),1):
        if "PIPE_" in l:
            print("%-14s:%d: %s" % (os.path.basename(fn), i, l.strip()[:130]))
