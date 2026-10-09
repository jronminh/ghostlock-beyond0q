import zipfile
p = '/mnt/e/Library/Desktop/ghostlock/lk.gz'
z = zipfile.ZipFile(p)
for n in z.namelist():
    print(repr(n), z.getinfo(n).file_size)
