F="/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s=open(F).read()
assert "CONFIGFS_READ_FILE" not in s
old="    {FOPS_READ_OFF, text_addr(CONFIGFS_READ_ITER)},"
new="    {FOPS_READ_OFF, text_addr(CONFIGFS_READ_FILE)},"
assert s.count(old)==1, s.count(old)
s=s.replace(old,new,1)
open(F,"w").write(s)
print("fops.c: refresh_fake_fops_text .read = configfs_read_file")
