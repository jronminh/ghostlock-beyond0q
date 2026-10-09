T="/root/ghostlock/ghostlock-oneplus/src/core/target.h"
s=open(T).read()
assert "#define DIRECT_MAP_END 0x0ULL" in s, "pattern"
s=s.replace("#define DIRECT_MAP_END 0x0ULL","#define DIRECT_MAP_END 0xffffffc400000000ULL")
open(T,"w").write(s)
print("target.h: DIRECT_MAP_END fixed")
