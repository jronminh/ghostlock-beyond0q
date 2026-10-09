import zipfile
z = zipfile.ZipFile('/mnt/e/Library/Desktop/ghostlock/kp20.gz')
t = z.read('dumpstate_lastkmsg.lst').decode('utf-8','replace').splitlines()
# find the ghostlock32 crash block
start = None
for i,l in enumerate(t):
    if 'ghostlock32' in l and ('Unable to handle' in l or 'BUG:' in l or 'Internal error' in l):
        start = i; break
print('ghost32 crash line =', start)
if start is None:
    for i,l in enumerate(t):
        if 'ghostlock32' in l and 'Call trace' in l:
            start = i-25; break
for l in t[max(0,start-6):start+55]:
    if '] ' in l: l = l.split('] ',1)[1]
    print(l)
