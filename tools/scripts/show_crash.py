import zipfile, sys
p = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 0
cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 80
z = zipfile.ZipFile(p)
names = [x for x in z.namelist() if 'lastkmsg' in x]
data = z.read(names[0] if names else z.namelist()[0]).decode('utf-8', 'replace').splitlines()
if n == 0:
    for i, l in enumerate(data):
        if 'Unable to handle kernel' in l or 'Internal error' in l or 'Kernel panic' in l:
            n = i
            break
for l in data[n:n + cnt]:
    if '] ' in l:
        l = l.split('] ', 1)[1]
    print(l)
