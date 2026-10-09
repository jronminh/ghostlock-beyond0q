import zipfile, re, sys
z=zipfile.ZipFile(sys.argv[1])
t=z.read("ocimem.lst").decode("utf-8","replace")
print("=== ocimem ===")
for l in t.splitlines():
    if re.search(r"(?i)kernel|boot|0x[89a-f][0-9a-f]{6}|image|dtb|load|entry|text_offset|ramdisk", l):
        print(l[:170])
