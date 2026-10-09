import os, re
root="/root/ghostlock/src/g9700"
def scan(pat, exts=(".c",".h")):
    r=re.compile(pat)
    out=[]
    for dp,_,fs in os.walk(root):
        if "/.git" in dp: continue
        for f in fs:
            if not f.endswith(exts): continue
            p=os.path.join(dp,f)
            try: t=open(p,errors="ignore").read()
            except: continue
            for i,l in enumerate(t.splitlines(),1):
                if r.search(l):
                    out.append("%s:%d: %s" % (p.replace(root+"/",""), i, l.strip()[:150]))
    return out
for pat in [r"PERF_SAMPLE_PHYS_ADDR", r"PERF_SAMPLE_ADDR", r"phys_addr\s*=", r"perf_sample_phys"]:
    print("==== %s ====" % pat)
    for l in scan(pat)[:15]:
        print("  ", l)
