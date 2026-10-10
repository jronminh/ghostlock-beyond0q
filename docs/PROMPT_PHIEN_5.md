# PROMPT BÀN GIAO — Phiên 5: **AUDIT** kết quả phiên 4

> Dán nguyên khối này vào đầu phiên mới. Nguồn sự thật: `BAN_GIAO_PHIEN4.md` (cùng thư mục)
> + repo WSL `~/ghostlock/ghostlock-oneplus` (patch phiên 3–4 **đã áp dụng, chưa commit**).

## 0. NHIỆM VỤ
**Kiểm toán (audit) các khẳng định của phiên 4.** **KHÔNG** phát triển tính năng mới. Mục tiêu là
tìm chỗ **sai / quá tự tin / giả thuyết đội lốt sự thật** trong `BAN_GIAO_PHIEN4.md` và trong code
đã sửa. Mỗi kết luận phải kèm **bằng chứng** (đoạn code + số dòng, disasm, log, hoặc dump), và ghi rõ
mức tin cậy.

## 1. Bối cảnh
- Máy **SM-G970W** (S10e, 4.14.190, **BL khoá cứng — không OEM unlock**, xác nhận; `MODULE_SIG_FORCE=y`).
- Exploit port GhostLock (futex PI UAF), hướng **B** (physrw qua configfs; KHÔNG pipe slab).
- Trần **RKP_KDP/DMAP_PROT/CFP** ⇒ chỉ sửa data.
- Thiết bị nối qua adb:
  `E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe`
- Build (WSL): `bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockA5`.

## 2. NHỮNG ĐIỀU CẦN AUDIT (theo thứ tự ưu tiên)

### A. Claim "configfs = arbitrary R/W không giới hạn độ dài"
- Đối chiếu `fs/configfs/file.c` (**4.14**, `~/ghostlock/src/g9700`) với cách `configfs_{read,write}_once`
  (util.c) đặt `page`/`bin_buffer`/`bin_buffer_size`/`cb_max_size`.
- **Câu hỏi:** đọc có thực sự bị chặn bởi `buffer->count` (= tiền tố tên ashmem) không? Ghi có đường
  **growth path** (`vmalloc`+`memcpy`+`vfree(bin_buffer)`) không — nếu `*ppos+count > bin_buffer_size`
  thì nó sẽ `vfree` chính `bin_buffer` (= target!) → đúng chưa? `configfs_write_once` có luôn đặt
  `bin_buffer_size = len` để tránh nhánh đó không?

### B. Claim "write mode-4 ở `[11]`, `[7]` là đường crash khi paint hụt"
- Đọc `kernel/locking/rtmutex.c` (4.14) `rt_mutex_adjust_prio_chain` (`[7] rt_mutex_dequeue`,
  `[11] rt_mutex_dequeue_pi/enqueue_pi`, `[5] retry`).
- Đối chiếu `fops.c` nhánh `SSOPT_EMPTY` (buf[0x10]=waiter, buf[0x18]=0, buf[0x20]=0) và nhánh full
  (VALUE,TARGET,0). Xác minh: với `SSOPT_EMPTY=1`, `[7]` có thực sự no-op (`RB_EMPTY_NODE`) và write
  có đến từ `[11]` không?
- Dump `kp_B18c.gz`/`kp_SCAN2.gz`: xác minh `pc: rb_erase_cached+0x20`, `x25==x0==waiter`, low14=0x3d10.

### C. Claim "reset là ở đường `cred`, KHÔNG phải walk"
- e2e6: 14/16 `cfi fops_before` + `physrw` → rồi reset. Kiểm lại: route chỉ gọi `try_cfi_stage` khi
  `calls>0 && success>0` ⇒ có thực sự suy ra "walk đã trả về" không? Hay `success` tăng ở chỗ khác?
- Dumps của e2e6 là `_WP` (không fault). **Có bằng chứng nào đủ để nói "KDP chặn cred" không?** Nếu
  không, phải hạ xuống "chưa xác định".

### D. Claim các offset (đo lại bằng probe, KHÔNG tin suông)
- `selinux_enforcing=0x02DC8CE8` (vs `selinux_state=0x02DC8CC8`) — kiểm bằng `kallsyms_fixed.txt` +
  `security/selinux/include/security.h` (`enforcing_enabled` trả `selinux_enforcing`).
- task `real_cred/cred/comm = 0x850/0x858/0x860` (lệch +8) — kiểm lại bằng dump (đã có `task[860]="ll_root_"`)
  VÀ xác định **shift bắt đầu từ field nào** (giữa 0x6AC và 0x848) — vì điều đó ảnh hưởng các offset
  khác (seccomp, atomic_flags, ...).
- workqueue 4.14, `subprocess_info`=96, `struct page` 0x30/0x20/0x18, kmalloc không cgroup.

### E. Claim "UMH hoàn tất sạch, không reset" (mới 1 mẫu) và "ENOKEY = fscrypt"
- Tìm log/dump chứng minh UMH **luôn** không reset (hiện chỉ 1 run lúc ~13:30).
- `ENOKEY (126)` từ `open()` của tiến trình do kernel sinh: có thật do fscrypt keyring không, hay
  giả thuyết? (Quan sát cũ: open lúc fail lúc pass.)

### F. An toàn relocation (B)
- Xác minh `UMH_WORK_OFF=0x400/UMH_DATA_OFF=0x480` và `binwrite_target=page+0x700` **nằm trong trang 4 KB**
  và **không đè** vùng còn sống (fops@0x319 và vùng fake-task 0x400–0xE18 — thật sự "chết" sau walk?).

## 3. RÀNG BUỘC
- **Không** sửa/triển khai thêm tính năng; chỉ đọc/đối chiếu/đo để audit. Nếu cần chạy, chỉ chạy
  **test đọc/kiểm chứng** (không thay đổi hành vi).
- **Không** đụng bootloader/partition/flash. Tránh `adb uninstall`.
- Build/đo trên fe2/WSL; `adb` từ local box như §1.
- Mỗi claim: nêu **bằng chứng dòng code / disasm / log / dump** + mức tin cậy (chắc/chưa chắc/sai).

## 4. KẾT QUẢ CẦN NỘP
1. Bảng: `Claim | Verdict (đúng/sai/chưa chắc) | Bằng chứng | Ghi chú`.
2. Danh sách **lỗi tìm được** (code hoặc lập luận) + cách sửa.
3. Danh sách **câu hỏi mở** còn lại (đặc biệt: nguyên nhân walk stall, KDP cred, fscrypt ENOKEY).
4. (Tuỳ chọn) 1–2 thí nghiệm tối thiểu để phân định các "chưa chắc".

## 5. Điểm bắt đầu gợi ý
- `BAN_GIAO_PHIEN4.md` §2 (flow), §3 (offset), §6 (lỗi/audit).
- Code: `src/core/{main.c,fops.c,util.c,root.c,umh_root.c,pipe_physrw.c}`, `src/devices/beyond0q/offsets.h`.
- Kernel: `~/ghostlock/src/g9700/{fs/configfs/file.c,kernel/locking/rtmutex.c,kernel/workqueue.c,kernel/umh.c}`.
- Dump: `kp_B14.gz`, `kp_BN`… (ZIP; member `dumpstate_lastkmsg.lst`), đọc bằng `kp_scan.py`.
