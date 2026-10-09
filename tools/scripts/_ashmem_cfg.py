import re
# ashmem.h constants
for p in ["/root/ghostlock/src/g9700/drivers/staging/android/ashmem.h",
          "/root/ghostlock/src/g9700/drivers/staging/android/uapi/ashmem.h"]:
    print("====", p)
    for i,l in enumerate(open(p,errors="ignore").read().splitlines(),1):
        if re.search(r"ASHMEM_NAME|ASHMEM_FULL|ASHMEM_PREFIX|ASHMEM_SET_NAME|#define ASHMEM", l):
            print("%4d %s" % (i, l.strip()))
# configfs write_bin_file signature
p="/root/ghostlock/src/g9700/fs/configfs/file.c"
L=open(p,errors="ignore").read().splitlines()
print("==== configfs write_bin_file / read_bin_file / write_iter ====")
for i,l in enumerate(L,1):
    if re.search(r"write_bin_file|read_bin_file|configfs_write_iter|configfs_read_iter|private_data", l):
        print("%4d %s" % (i, l.strip()[:150]))
