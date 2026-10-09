import re,glob,os
CORE="/root/ghostlock/ghostlock-oneplus/src/core"
pat=re.compile(r"page_base\s*=|extern .*page_base|uintptr_t page_base")
for fn in sorted(glob.glob(CORE+"/*.c")+glob.glob(CORE+"/*.h")):
    for i,l in enumerate(open(fn,errors="ignore").read().splitlines(),1):
        if pat.search(l):
            print("%-14s:%d: %s" % (os.path.basename(fn), i, l.strip()[:120]))
