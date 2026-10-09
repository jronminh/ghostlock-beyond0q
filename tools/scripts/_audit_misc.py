import re
m="/root/ghostlock/src/g9700/drivers/char/misc.c"
t=open(m,errors="ignore").read().splitlines()
for i,l in enumerate(t):
    if "misc_open" in l and "static int" in l:
        print("--- misc_open @%d ---" % (i+1))
        for j in range(i, min(len(t), i+40)):
            print(t[j])
        break
print("\n=== JOPP refs ===")
import os
for dp,_,fs in os.walk("/root/ghostlock/src/g9700"):
    if "/.git" in dp: continue
    for f in fs:
        if not f.endswith((".c",".h",".S")): continue
        p=os.path.join(dp,f)
        try: t2=open(p,errors="ignore").read()
        except: continue
        for i,l in enumerate(t2.splitlines(),1):
            if re.search(r"JOPP|JOP[key ]|jump[_ ]oriented", l, re.I):
                print("%s:%d: %s" % (p.split("g9700/")[-1], i, l.strip()[:140]))
