import re
p="/root/ghostlock/src/g9700/drivers/staging/android/ashmem.c"
L=open(p,errors="ignore").read().splitlines()
# print struct ashmem_range / ashmem_state and ashmem_open / set_name / ioctl
print("=== struct ashmem_range / ashmem_state ===")
for i,l in enumerate(L):
    if re.search(r"struct ashmem_(range|state)\s*\{", l):
        for j in range(i, min(len(L), i+34)):
            print("%4d %s" % (j+1, L[j]))
        print("---")
print("=== ashmem_open ===")
for i,l in enumerate(L):
    if "ashmem_open" in l and "(" in l and ("{" in l or l.rstrip().endswith(")")):
        for j in range(i, min(len(L), i+30)): print("%4d %s" % (j+1, L[j]))
        break
print("=== set_name / SET_NAME ===")
for i,l in enumerate(L):
    if "set_name" in l and ("(" in l):
        for j in range(i, min(len(L), i+34)): print("%4d %s" % (j+1, L[j]))
        break
print("=== private_data refs ===")
for i,l in enumerate(L):
    if "private_data" in l: print("%4d %s" % (i+1, l.strip()[:140]))
