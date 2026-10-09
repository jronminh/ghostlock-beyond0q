#!/usr/bin/env python3
"""patch_ssopt_nocfi.py

SSOPT_NO_CFI=1 : bỏ try_cfi_stage() trong route setsockopt.
Lý do: nếu lần ghi PI *thành công* (ashmem_misc.fops đã trỏ vào trang giả) thì
try_cfi_stage() mở ashmem rồi write() qua fops giả -> có thể treo/crash kernel,
làm mất luôn khả năng đọc kết quả.  Với NO_CFI ta chỉ chạy paint + walk rồi đọc
peek để biết chắc walk đã ghi gì (page[0x108] == TARGET nếu chain[7] chạy).
"""
F = "/root/ghostlock/ghostlock-oneplus/src/core/fops.c"
s = open(F).read()
old = """    if (calls > 0 && success > 0) {
      if (!route_only_mode) {
        try_cfi_stage();
      }
      break;
    }"""
new = """    if (calls > 0 && success > 0) {
      if (!route_only_mode && !env_flag("SSOPT_NO_CFI", 0)) {
        try_cfi_stage();
      } else if (env_flag("SSOPT_NO_CFI", 0)) {
        pr_info("ssopt NO_CFI: walk done (calls=%d success=%d), skipping cfi "
                "stage\\n", calls, success);
        fsync(1);
      }
      break;
    }"""
assert s.count(old) == 1, ("nocfi", s.count(old))
s = s.replace(old, new, 1)
open(F, "w").write(s)
print("fops.c: SSOPT_NO_CFI to skip try_cfi_stage() during diagnostics")
