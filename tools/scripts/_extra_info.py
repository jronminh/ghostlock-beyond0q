import zipfile, re, sys
z=zipfile.ZipFile(sys.argv[1])
for member in ("store_extra_info.lst","reset_summary.html","history_of_auto_comment.txt"):
    if member not in z.namelist(): continue
    t=z.read(member).decode("utf-8","replace")
    print("=====", member, len(t))
    for l in t.splitlines():
        if re.search(r"(?i)kernel offset|phys|0x8[0-9a-f]{6,}|ram|dram|image|load addr|start addr|kimage", l):
            print(" ", l.strip()[:170])
