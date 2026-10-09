import re
U="/root/ghostlock/ghostlock-oneplus/src/core/util.c"
F="/root/ghostlock/ghostlock-oneplus/src/core/fops.c"

s=open(U).read()
assert "FIX_RW" not in s

# 1) put_fake_fops_table
old="""  put64(p, off + FOPS_READ_OFF, 0);
  put64(p, off + FOPS_WRITE_OFF, 0);
  put64(p, off + FOPS_READ_ITER_OFF, text_addr(CONFIGFS_READ_ITER));
  put64(p, off + FOPS_WRITE_ITER_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
"""
new="""  /* FIX_RW: configfs_{read,write}_bin_file are the OLD-style .read/.write
   * ops (file,buf,count,ppos), not .{read,write}_iter.  Put them in the
   * .read/.write slots; leave read_iter/write_iter = 0. */
  put64(p, off + FOPS_READ_OFF, text_addr(CONFIGFS_READ_ITER));
  put64(p, off + FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, off + FOPS_READ_ITER_OFF, 0);
  put64(p, off + FOPS_WRITE_ITER_OFF, 0);
"""
assert s.count(old)==1, ("put_fake_fops_table", s.count(old))
s=s.replace(old,new,1)

# 2) repair function
old2="""  put64(p, FOPS_READ_OFF, 0);
  put64(p, FOPS_WRITE_OFF, 0);
  put64(p, FOPS_READ_ITER_OFF, text_addr(CONFIGFS_READ_ITER));
  put64(p, FOPS_WRITE_ITER_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
"""
new2="""  put64(p, FOPS_READ_OFF, text_addr(CONFIGFS_READ_ITER));
  put64(p, FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER));
  put64(p, FOPS_READ_ITER_OFF, 0);
  put64(p, FOPS_WRITE_ITER_OFF, 0);
"""
assert s.count(old2)==1, ("repair", s.count(old2))
s=s.replace(old2,new2,1)
open(U,"w").write(s)
print("util.c: .read/.write slots fixed")

f=open(F).read()
old3="""    {FOPS_READ_ITER_OFF, text_addr(CONFIGFS_READ_ITER)},
    {FOPS_WRITE_ITER_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER)},
"""
new3="""    {FOPS_READ_OFF, text_addr(CONFIGFS_READ_ITER)},
    {FOPS_WRITE_OFF, text_addr(CONFIGFS_BIN_WRITE_ITER)},
"""
assert f.count(old3)==1, ("refresh", f.count(old3))
f=f.replace(old3,new3,1)
open(F,"w").write(f)
print("fops.c: refresh_fake_fops_text fixed")
