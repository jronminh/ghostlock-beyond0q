#!/usr/bin/env python3
"""patch_fops_offsets.py

Sửa FOPS_*_OFF cho ĐÚNG layout `struct file_operations` của kernel 4.14.190 của
máy (đọc trực tiếp từ /root/ghostlock/src/g9700/include/linux/fs.h):

  owner 0x00, llseek 0x08, read 0x10, write 0x18, read_iter 0x20, write_iter 0x28,
  iterate 0x30, iterate_shared 0x38, poll 0x40, unlocked_ioctl 0x48,
  compat_ioctl 0x50, mmap 0x58, open 0x60, flush 0x68, release 0x70, fsync 0x78,
  fasync 0x80, lock 0x88, sendpage 0x90, get_unmapped_area 0x98, check_flags 0xa0,
  flock 0xa8, splice_write 0xb0, splice_read 0xb8, setlease 0xc0, fallocate 0xc8,
  show_fdinfo 0xd0, copy_file_range 0xd8, clone_file_range 0xe0,
  dedupe_file_range 0xe8.

Bảng cũ lệch +8 ở hầu hết field (llseek 0x10, read 0x18, write_iter 0x30,
ioctl 0x50, mmap 0x60, open 0x68, release 0x78, show_fdinfo 0xd8) nhưng lại đúng
ở owner 0x00 và splice_read 0xb8  => sau khi redirect: f_op->write_iter trỏ vào
configfs_read_iter (=> EINVAL), còn f_op->read/write... trỏ vào giá trị trang
(=> wild call => treo máy/watchdog).

Chú ý: `repair_fake_fops_llseek()` sửa đúng slot bị __rb_change_child() ghi đè;
với layout ĐÚNG thì slot đó CHÍNH LÀ llseek ([fake_fops+0x08]) => khớp.
"""
T = "/root/ghostlock/ghostlock-oneplus/src/core/target.h"
s = open(T).read()

pairs = [
    ("#define FOPS_LLSEEK_OFF       0x10", "#define FOPS_LLSEEK_OFF       0x08"),
    ("#define FOPS_READ_OFF         0x18", "#define FOPS_READ_OFF         0x10"),
    ("#define FOPS_WRITE_OFF        0x20", "#define FOPS_WRITE_OFF        0x18"),
    ("#define FOPS_READ_ITER_OFF    0x28", "#define FOPS_READ_ITER_OFF    0x20"),
    ("#define FOPS_WRITE_ITER_OFF   0x30", "#define FOPS_WRITE_ITER_OFF   0x28"),
    ("#define FOPS_IOCTL_OFF        0x50", "#define FOPS_IOCTL_OFF        0x48"),
    ("#define FOPS_COMPAT_IOCTL_OFF 0x58", "#define FOPS_COMPAT_IOCTL_OFF 0x50"),
    ("#define FOPS_MMAP_OFF         0x60", "#define FOPS_MMAP_OFF         0x58"),
    ("#define FOPS_OPEN_OFF         0x68", "#define FOPS_OPEN_OFF         0x60"),
    ("#define FOPS_RELEASE_OFF      0x78", "#define FOPS_RELEASE_OFF      0x70"),
    ("#define FOPS_SHOW_FDINFO_OFF  0xd8", "#define FOPS_SHOW_FDINFO_OFF  0xd0"),
]
for old, new in pairs:
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new, 1)

# ghi chú nguồn sự thật ngay trên bảng
old = "#define FOPS_OWNER_OFF        0x00"
new = ("/* Offsets theo dung struct file_operations cua kernel 4.14.190 (fs.h cua may,\n"
       " * xem patch_fops_offsets.py). Ban cu lech +8 o hau het field. */\n"
       "#define FOPS_OWNER_OFF        0x00")
assert s.count(old) == 1, ("comment", s.count(old))
s = s.replace(old, new, 1)
open(T, "w").write(s)
print("target.h: FOPS_*_OFF fixed to the real 4.14 file_operations layout")
