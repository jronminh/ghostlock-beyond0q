import re
CORE="/root/ghostlock/ghostlock-oneplus/src/core"
def grep(fn, pat, ctx=0):
    L=open(CORE+"/"+fn,errors="ignore").read().splitlines()
    for i,l in enumerate(L):
        if re.search(pat,l):
            for j in range(max(0,i-ctx), min(len(L), i+ctx+1)):
                print("%s:%d: %s" % (fn, j+1, L[j]))
            print("-")
for fn in ("util.c","common.h","target.h"):
    for pat in [r"FOPS_TABLE_OFF", r"SKB_FRAG_BIAS", r"SKB_DATA_DELTA", r"put_fake_fops_table", r"#define LOCK_OFF", r"#define FOPS_OFF"]:
        grep(fn, pat, 0)
