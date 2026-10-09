import re
p="/root/ghostlock/src/g9700/arch/arm64/include/asm/memory.h"
t=open(p).read()
for m in re.finditer(r".*ARM64_MEMSTART.*", t):
    print(m.group(0))
print("--- init.c 540-561 ---")
t2=open("/root/ghostlock/src/g9700/arch/arm64/mm/init.c").read().splitlines()
for i in range(539,561):
    print(i+1, t2[i])
