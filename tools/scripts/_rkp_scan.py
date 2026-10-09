import re, os
root="/root/ghostlock/src/g9700"
pats = {
 "rkp.h CFP/KDP": re.compile(r"(RKP_CFP|RKP_KDP|rkp_cfp|rkp_kdp|JOPP|0x00be7bad|0xbe7bad)"),
 "dmap/ro protect": re.compile(r"(rkp_ro_alloc|set_memory_ro|protect_kernel|pageattr|rodata)"),
}
# list files mentioning rkp
hits=[]
for dp,_,fs in os.walk(root):
    if "/.git" in dp: continue
    for f in fs:
        if not f.endswith((".c",".h")): continue
        p=os.path.join(dp,f)
        try: t=open(p,errors="ignore").read()
        except: continue
        if re.search(r"rkp|RKP", t) and ("cfp" in t.lower() or "kdp" in t.lower() or "dmap" in t.lower()):
            hits.append((p, len(re.findall(r"(?i)rkp", t))))
hits.sort(key=lambda x:-x[1])
for p,n in hits[:25]:
    print("RKP file:", p.replace(root+"/",""), "rkp_mentions=",n)
