import re, bisect
syms=[]
for l in open('/root/ghostlock/kernel/kallsyms_fixed.txt'):
    m=re.match(r'([0-9a-f]+)\s+(\w)\s+(\S+)',l)
    if m: syms.append((int(m.group(1),16),m.group(3)))
syms.sort(); a=[x for x,_ in syms]
for t in (0xffffff8008207504,0xffffff80096da380,0xffffff80096b9400,0xffffff800942f040):
    i=bisect.bisect_right(a,t)-1
    print(hex(t),'->',hex(syms[i][0]),syms[i][1])
