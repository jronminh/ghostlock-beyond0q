import zipfile
z = zipfile.ZipFile('/mnt/e/Library/Desktop/ghostlock/lk.gz')
data = z.read('dumpstate_lastkmsg.lst')
open('/mnt/e/Library/Desktop/ghostlock/lastkmsg_june.lst','wb').write(data)
print('extracted', len(data))
txt = data.decode('utf-8', 'replace')
lines = txt.splitlines()
keys = ('rt_mutex', 'Call trace', 'Unable to handle', 'Kernel panic', 'Internal error',
        'pc :', 'lr :', 'x21 :', 'x0 :', 'Oops', 'BUG:', 'panic', 'ashmem', 'ghostlock')
for i, l in enumerate(lines):
    if any(k in l for k in keys):
        print(i, l[:200])
