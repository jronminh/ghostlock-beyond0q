import re
p="/root/ghostlock/src/g9700/fs/configfs/file.c"
L=open(p,errors="ignore").read().splitlines()
print("=== struct configfs_buffer ===")
for i,l in enumerate(L):
    if re.search(r"struct configfs_buffer\s*\{", l):
        for j in range(i, min(len(L), i+40)): print("%4d %s"%(j+1,L[j]))
        break
print("\n=== configfs_write_bin_file ===")
for i,l in enumerate(L):
    if "configfs_write_bin_file" in l and "ssize_t" in l:
        for j in range(i, min(len(L), i+42)): print("%4d %s"%(j+1,L[j]))
        break
print("\n=== configfs_read_bin_file ===")
for i,l in enumerate(L):
    if "configfs_read_bin_file" in l and "ssize_t" in l:
        for j in range(i, min(len(L), i+42)): print("%4d %s"%(j+1,L[j]))
        break
