import re, zipfile
z=zipfile.ZipFile("/mnt/e/Library/Desktop/ghostlock/kp85.gz")
L=z.read("dumpstate_lastkmsg.lst").decode("utf-8","replace").splitlines()
print("first 40 lines:")
for l in L[:40]: print("  ", l.split("]")[-1].strip()[:150])
print("\n=== memory/phys lines ===")
for l in L[:4000]:
    if re.search(r"[Mm]emory:|memblock|0x8008|0x8000|Kernel code|Virtual kernel|earlycon|dram|DRAM|Memory:", l):
        print("  ", l.split("]")[-1].strip()[:160])
