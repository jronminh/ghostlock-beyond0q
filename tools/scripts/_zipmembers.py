import zipfile, re, sys
z=zipfile.ZipFile(sys.argv[1])
for n in z.namelist():
    print("%-60s %d" % (n, z.getinfo(n).file_size))
