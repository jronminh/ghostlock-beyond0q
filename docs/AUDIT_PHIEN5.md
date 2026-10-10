# AUDIT PHIÊN 5 — GhostLock SM-G970W (hướng B)

> Nhiệm vụ: **kiểm toán** các khẳng định của `BAN_GIAO_PHIEN4.md` + code đã sửa (uncommitted).
> Không thêm tính năng. Chỉ đọc/đối chiếu/đo read-only.
>
> Nguồn đã dùng:
> - Repo WSL `~/ghostlock/ghostlock-oneplus` (working tree, uncommitted) + `git diff` vs HEAD.
> - Kernel OSRC `~/ghostlock/src/g9700` (source + `out/.config` + `out/kernel/probe_*.o`).
> - `~/ghostlock/kernel/kallsyms_fixed.txt`, `vmlinux.elf` (⚠ symbol nhãn bị lệch — xem §E).
> - Dump `E:\Library\Desktop\ghostlock\kp*.gz`, log `gl_*.log`, `_dn_e2e*.log`.
> - **Thiết bị thật** (read-only qua adb): `R58M21XM7DD`, `SM-G970W`, `4.14.190-…G970WVLU9IXE1`.
> - Mục tiêu lệch offset đã chốt bằng **thí nghiệm biên dịch lại probe** (`_audit_rebuild.sh`, read-only, không đụng máy).

---

## 1. BẢNG KẾT LUẬN

| # | Claim (BAN_GIAO_PHIEN4 / code) | Verdict | Bằng chứng | Ghi chú |
|---|---|---|---|---|
| A1 | configfs = arbitrary R/W **không giới hạn độ dài** | **ĐÚNG (kết luận)** — nhưng lập luận phải nói rõ "đọc bị chặn bởi `buffer->count`" | `fs/configfs/file.c:129-130` (`simple_read_from_buffer(...,buffer->page,buffer->count)`); `util.c:1312-1330`; `common.h:81-82` | Cơ chế: overlay `struct configfs_buffer` lên `asma->name` (`ashmem.c:54-60,265-267`), `SET_NAME` ghi ở `name+11` (`ashmem.c:564`). `count` (off 0x00) = 8 byte đầu `"dev/ashm"` = `ASHMEM_PREFIX_COUNT` (0x6d6873612f766564) nên gần như vô hạn. |
| A2 | Đọc dùng `page` + `pos`, không đụng `to_frag()` | **ĐÚNG** khi `needs_read_fill==0` | `util.c:1318` đặt `CFG_NEEDS_READ_FILL_OFF=0`; `file.c:122-130` (bỏ `fill_read_buffer`) | Nếu `needs_read_fill!=0` thì `fill_read_buffer→to_frag→buffer->attr->show` sẽ deref rác. |
| A3 | Ghi có **growth path `vmalloc+memcpy+vfree(bin_buffer)`** (vfree chính target) | **ĐÚNG — nhánh tồn tại** | `file.c:335-361` (điều kiện `*ppos+count > bin_buffer_size` → `vfree(buffer->bin_buffer)` ở dòng 353) | |
| A4 | `configfs_write_once` luôn đặt `bin_buffer_size=len` để tránh A3 | **ĐÚNG** | `util.c:1297` (`put32(blob, CFG_BIN_BUFFER_SIZE_OFF-…, len)`); `pwrite(...,0)` ⇒ `0+len > len` = false | |
| A5 | Offset `struct configfs_buffer` (CFG_*) khớp kernel | **ĐÚNG (xác nhận thực nghiệm)** | `target.h:199-203`; `cfi fops_before ret=8` + `cfi write ret=35`/`cfi read ret=35` trong `BAN_GIAO.md` ⇒ primitive đọc/ghi chạy đúng ⇒ các field `page/bin_buffer/bin_buffer_size/cb_max_size` đúng | `struct configfs_buffer` (0x00 count, 0x08 pos, 0x10 page, 0x20 mutex, 0x48 needs_read_fill, 0x50 bin_buffer, 0x58 bin_buffer_size, 0x5c cb_max_size) với `sizeof(mutex)=0x28` nhờ **CONFIG_KPERFMON=y** (Samsung thêm `unsigned long time`). ⚠ Danh sách `cfi *_ret=35` chỉ có trong **doc**, không có trong log thô đã lưu (log thô chỉ có `ret=8` của e2e6 và `ret=-1 errno=22` của QA). |
| B1 | Dump `kp_SCAN2` xác nhận `pc: rb_erase_cached+0x20`, `x25==x0==waiter`, low14=0x3d10 | **ĐÚNG** | `kp_SCAN2.gz` (== `kp_B14.gz`, process **ghostlockB21**), dòng 4298-4340: `pc rb_erase_cached+0x20`, `lr rt_mutex_adjust_prio_chain+0x310`, `x0=x25=0xffffff8011c9bd10` (low14 `0x3d10`), `x1=ffff…c008`, `x9=64e716f4e0b07ba4` (rác) | |
| B2 | Crash là **`[7] rt_mutex_dequeue`** (write hụt từ `[7]`) | **ĐÚNG** | `rtmutex.c:294-302` `rb_erase_cached(&waiter->tree_entry,&lock->waiters)` so với `:327-335` `&waiter->pi_tree_entry`. Panic có `x0=waiter` (=`tree_entry@0x00`) và `x1=&lock->waiters` (=`page_base+8`) ⇒ **đúng call site `[7]`**. | Với `waiter_compact=1`, `pi_tree_entry@0x18` ⇒ nếu là `[11]` thì `x0=waiter+0x18`, không khớp. |
| B3 | `SSOPT_EMPTY=1` làm `[7]` no-op (`RB_EMPTY_NODE`) | **ĐÚNG** | `fops.c:578-592` sơn `tree_entry.__rb_parent_color = ssopt_leaked_waiter`; `rtmutex.c:297` (`if (RB_EMPTY_NODE(&waiter->tree_entry)) return;`) | Crash xảy ra ⇒ paint **đã bị đè** (đúng giả thuyết handoff). |
| B4 | "write mode-4 ở `[11]`, `[7]` là đường crash" | **CHƯA CHẮC — phụ thuộc cờ; có mâu thuẫn nội bộ** | `util.c:530-534, 594-599` nói write từ `[11]`; **nhưng** `util.c:642-648` nói owner=0 ⇒ chain dừng ở `[9]` và **`[7]` chính là write**. Default code `SSOPT_OWNER0=1` (`util.c:647,660`) ⇒ dừng sau `[7]`; lệnh chạy tay dùng `SSOPT_OWNER0=0` mới tới `[11]`. | Mệnh đề tuyệt đối "[7] không bao giờ write" **SAI**. Chỉ đúng khi `SSOPT_EMPTY=1` **và** leak waiter thành công. |
| C1 | Route gọi `try_cfi_stage` chỉ khi `calls>0 && success>0` ⇒ suy ra "walk đã trả về" | **ĐÚNG** | `fops.c:644-645` reset `consumer_calls/success` **mỗi attempt**; `main.c:240` tăng `consumer_success` chỉ khi `sched_setattr_tid` trả 0 (hoặc fallback futex OK). `fops.c:767`. | `success>0` ⇒ syscall walk trả về (không hang) là suy luận hợp lệ. |
| C2 | e2e6 = 14/16 redirect OK rồi reset trên đường **cred** | **ĐÚNG (reset ở nhánh cred)** | `_dn_e2e6.log`: attempt 1 & 7 không có kết quả; 14 attempt còn lại có `cfi fops_before ret=8 … || physrw: configfs-only mode` rồi `no root; reboot`. Lệnh `_dn_e2e6.ps1` dùng `SKIP_UMH=1` (⇒ chỉ còn nhánh cred). | |
| C3 | Reset do **KDP chặn cred** | **CHƯA XÁC ĐỊNH** (KDP vẫn khả thi, chưa chứng minh) | Không có dump nào có Oops trên đường cred; `kp_cred.gz` không Oops; **`kp_B18b.gz`/`kp_B18c.gz` (process ghostlockB18) cũng KHÔNG Oops** — reset/hang **im lặng**. Reset im lặng là **phù hợp với KDP** (RKP reset không để lại Oops) **và** cũng phù hợp với hard-lockup. | ⚠ **Giả thuyết "offset cred sai" ĐÃ BỊ BÁC BỎ** (xem §2.4/§6): `ghostlockB18_a64` đã có offset đúng. |
| D1 | `selinux_enforcing=0x02DC8CE8` (≠ `selinux_state=0x02DC8CC8`) | **ĐÚNG** | `kallsyms_fixed.txt:133933-133934`; `security/selinux/hooks.c:207`; `include/security.h:116-121` (`enforcing_enabled()` trả global `selinux_enforcing`, `CONFIG_SECURITY_SELINUX_DEVELOP=y` xác nhận trên máy). | |
| D2 | task `real_cred/cred/comm = 0x850/0x858/0x860` (+8) | **ĐÚNG** | Thí nghiệm §4.1: biên dịch lại `probe_offsets.c` với `-DCONFIG_CC_STACKPROTECTOR=1` ⇒ `0x850/0x858/0x860`. Disasm crash đọc `[x19,#0x948]` = pi_blocked_on ⇒ +8. | |
| D3 | Shift bắt đầu từ đâu (giữa 0x6AC và 0x848)? | **ĐÚNG — bắt đầu NGAY SAU `tgid`** | `include/linux/sched.h:905-911`: `pid; tgid;` rồi `#ifdef CONFIG_CC_STACKPROTECTOR unsigned long stack_canary;` ⇒ **`stack_canary` là nguyên nhân +8**. | Hệ quả: `real_parent` phải **0x6B8** (offsets.h để 0x6B0 – SAI); `seccomp` phải **0x900** (offsets.h 0x8F8 – SAI). `atomic_flags=0x670` (trước `pid`) **đúng**. |
| D4 | `struct subprocess_info = 96` | **ĐÚNG** | `umh_root.c:79` `_Static_assert(==96)`; `include/linux/umh.h` (work 32 + complete/path/argv/envp 8×4 + wait/retval 4+4 + init/cleanup/data 8×3 = 96). | |
| D5 | `struct page` `slab_cache=0x30, compound_head=0x20, page_type=0x18` | **CHƯA XÁC MINH** | Không có bằng chứng đo trong tài liệu; hướng B **không dùng** pipe path nên vô hại. | |
| D6 | kmalloc: chỉ `NORMAL=0,RECLAIM=1,DMA=2`, **không cgroup** | **ĐÚNG** | `include/linux/slab.h:274-281`; `out/.config CONFIG_ZONE_DMA=y`; `common.h:98-99` (`KMALLOC_CGROUP_TYPE=2` = DMA, đặt tên sai). | |
| E1 | UMH "sạch, không reset" chỉ **1 mẫu** | **ĐÚNG nhưng đếm thiếu** | `_dn_e2e.log` có **2 mẫu** `umh: result wake=1 complete=1 retval=0` (attempt 1,2) và máy **không reset** (log tiếp tục), + 1 mẫu handoff ~13:30 ⇒ ≥3. | |
| E2 | UMH chạy **uid 0 thật** | **KHÁ CHẮC** | `retval=0`/`complete=1` (kernel báo exec OK); **`.ghostlock_root.log` được tạo bởi tiến trình `owner root`** (0 byte) — chỉ tiến trình root mới tạo được ⇒ con UMH **đã chạy**. Nhưng chuỗi `umh_uid_0_euid_0_gid_0` **không có** trong log đã lưu, và file 0 byte chưa rõ vì sao chưa ghi nội dung. | Nên thu `/data/local/tmp/umh_root_proof` để chốt `uid=0,euid=0,gid=0`. |
| E3 | `ENOKEY` do **fscrypt keyring** | **CHƯA CHẮC (giả thuyết)** | Không có log nào chứa `ENOKEY` trong artifact; `_dn_session4.md:10-11` chỉ là suy đoán. | |
| E4 | Thiết kế UMH không `kfree` fake `subprocess_info` | **ĐÚNG (tốt)** | `kernel/umh.c:46-58` `umh_complete`: `comp=xchg(&complete,NULL)`; fake đặt `complete=completion_addr` (`umh_root.c:278-303`) ⇒ đi nhánh `complete()`, **không** gọi `call_usermodehelper_freeinfo→kfree`. | Tránh được `kfree` lên page memfd. |
| F1 | `UMH_WORK_OFF=0x400`, `UMH_DATA_OFF=0x480`, `binwrite_target=page+0x700` nằm trong 1 trang 4 KB | **ĐÚNG** | `page` offset = `.c` offset + `SKB_DATA_DELTA(-0xE80)`: fake_task 0x1280→**0x400**; fops bảng @0x319; `binwrite_target` LOCK_OFF+0x700→**0x700**. UMH data kết thúc 0x5E8. | |
| F2 | UMH scratch **không đè vùng còn sống** | **ĐÚNG có điều kiện** | `UMH_WORK_OFF=0x400` **trùng** đúng vị trí `fake_task` (0x400). An toàn **vì** `install_umh_root` chạy trong `try_cfi_stage` **sau khi route kết thúc** (không còn walk) ⇒ fake_task đã chết; bảng fops @0x319 không bị đụng. | Nếu tương lai gọi walk sau UMH → sẽ hỏng. |

---

## 2. LỖI TÌM ĐƯỢC + CÁCH SỬA

### 2.1 ⚠ NGHIÊM TRỌNG — Nhãn dump sai (handoff trỏ nhầm file)
`BAN_GIAO_PHIEN4.md §6` gán panic `rb_erase_cached+0x20` cho `kp_B18c.gz`/`kp_SCAN2.gz`.
Thực tế (quét `dumpstate_lastkmsg.lst`):
- `kp_SCAN2.gz` == `kp_B14.gz` → process **ghostlockB21** có panic `rb_erase_cached+0x20`.
- `kp_B18.gz` → process **ghostlockB14**, panic **khác**: `configfs_read_file → simple_read_from_buffer → __arch_copy_to_user` fault `VA=0x78` (`x4=0x6d6873612f766564`).
- `kp_B18c.gz` → ghostlockB18, **KHÔNG có Oops** (chỉ hang/watchdog).

**Sửa:** tra dump theo **tên process** (đã ghi ở §9.1 `PHIEN_2026-10-10.md`), đừng tin tên file.

### 2.2 Offset probe bị lệch +8 vì `out/.config` khác máy
`out/kernel/probe_offsets.o` (mtime 13:17) biên dịch với `out/.config`, trong đó **`CONFIG_CC_STACKPROTECTOR_NONE=y`**, còn firmware máy có **`CONFIG_CC_STACKPROTECTOR_STRONG=y`** (+`CONFIG_CC_STACKPROTECTOR=y`).
`stack_canary` (`sched.h:908-911`) nằm ngay sau `tgid` ⇒ mọi field sau `tgid` +8.
⇒ `probe_offsets.o`, `beyond0q_4.14.h`, `target_4.14.h` (nhánh dùng chúng) đều **sai +8** cho `real_parent/cred/real_cred/comm/seccomp/pi_*`.
**Sửa:** build probe với `-DCONFIG_CC_STACKPROTECTOR=1` (đã kiểm: ra đúng `cred=0x858, comm=0x860, pi_blocked_on=0x948`). Cập nhật `out/.config` cho khớp máy (bật `CC_STACKPROTECTOR`).

### 2.3 Offset còn "cũ" (+0) trong `offsets.h` — hậu quả
`src/devices/beyond0q/offsets.h` chỉ sửa `cred/comm/real_cred/pi_*` (+8) ở phiên 3–4, **bỏ sót**:
- `.task_real_parent = 0x6B0` → đúng phải **0x6B8** (hiện **không dùng**).
- `.task_seccomp = 0x8F8` → đúng phải **0x900** (patch seccomp **bị skip** — `root.c:476`).
- `.task_atomic_flags = 0x670` → **đúng** (trước `pid`).
⇒ Hiện vô hại, nhưng nếu bật lại patch seccomp sẽ ghi sai. **Sửa:** `+8` cho `real_parent` và `seccomp`; bỏ `TASK_REAL_PARENT` nếu không dùng.

### 2.4 ⚠ ĐÍNH CHÍNH (tự kiểm): giả thuyết "offset cred sai" **SAI**
Bản nháp đầu của audit nghi reset cred ở e2e6 do build B18 dùng offset cred *không canary* (`0x848/0x850`).
**Đã kiểm bằng byte-pattern trong chính binary** (`known_offsets[]` trong `.rodata`):
```
ghostlockB14_a64 @833284: atomic=0x670 real_cred=0x848 cred=0x850 comm=0x858   (CŨ)
ghostlockB18_a64 @833284: atomic=0x670 real_cred=0x850 cred=0x858 comm=0x860   (MỚI)
ghostlockB25_a64 @833284: atomic=0x670 real_cred=0x850 cred=0x858 comm=0x860   (MỚI)
```
⇒ **B18/B25 đã có offset cred ĐÚNG**; chỉ **B14** là bản cũ. Vậy reset e2e6 (chạy B18) **KHÔNG do offset cred**.
Kết luận đúng: reset e2e6 là **im lặng (không Oops)** — xảy ra sau redirect, trong nhánh cred; nguyên nhân **chưa xác định**, KDP vẫn khả thi (reset im lặng) nhưng chưa chứng minh.
⚠ Lưu ý: `.task_seccomp=0x8F8` vẫn là giá trị *không canary* ở **cả** B18/B25 (đúng phải `0x900`) — may là patch seccomp đang bị skip.

### 2.4b Ghi chú bổ sung: `cfi write ret=35` chỉ có trong doc
Chuỗi `cfi write ret=35` / `cfi read ret=35` xuất hiện ở `BAN_GIAO.md`, `BAN_GIAO_PHIEN4.md`, `PROMPT_PHIEN_4.md` — **không** có trong log thô nào đã lưu (`gl_*.log` chỉ có `ret=-1 errno=22`, hoặc `fops_before ret=8`).
Bằng chứng thô thật cho (A) là dòng `cfi fops_before ret=8 value==want==fake_fops` trong `_dn_e2e6.log` (14/16) — đủ để kết luận redirect OK.

### 2.5 Default `SSOPT_HOLD=1` là cấu hình **hỏng** theo chính phiên 2/3
`util.c:711-716` hold bằng `select(64, empty-pipe)`, nhưng `PHIEN_2026-10-10.md §11` chứng minh `core_sys_select` giữ `long stack_fds[32]` tại `SP0-0x210..SP0-0x110`, **trùm `waiter`** ⇒ **xoá paint**. Default code là `1` (`fops.c:661,711`), lệnh handoff dùng `0`.
**Sửa:** đổi default `SSOPT_HOLD=0` (hoặc xoá hẳn hold; dùng spin-park).

### 2.6 Mâu thuẫn comment `[7]` vs `[11]`
Như B4. **Sửa:** ghi rõ nhánh: `SSOPT_EMPTY=1 && leak OK` → write qua `[11]`; ngược lại (`SSOPT_OWNER0=1`) → write qua `[7]`. Sửa comment `util.c:642-648` hoặc `:530-534` cho khớp.

### 2.7 Build cũ vẫn dùng `selinux_state`
`gl_QA_peek.log:35` target `W1 = 0xffffffc002dc8cc8` (=`selinux_state`) ⇒ binary QA cũ. `target_4.14.h:8`, `beyond0q_4.14.h:24` **vẫn** ghi `selinux_state`. **Sửa:** build lại mọi binary với `0x02DC8CE8`; sửa 2 header phụ.

### 2.8 Nhận xét nhỏ: `vmlinux.elf` nhãn hàm bị lệch
`--disassemble=<sym>` cho ra code của hàm khác (vd `rt_mutex_adjust_prio_chain` → thực ra là `rt_mutex_adjust_pi`). **Đừng** dùng `vmlinux.elf` để suy offset theo tên hàm; dùng dump runtime (đã symbolize) hoặc probe.

---

## 3. CÂU HỎI MỞ

1. **Nguyên nhân walk stall**: vẫn chưa tách được "hard-lockup (spinlock) " vs "panic `rb_erase`". Dump chứng minh nhánh panic; nhánh hang chỉ có watchdog + không trace. Tỉ lệ thực **chưa đo** (handoff nói đúng). `SSOPT_HOLD` không cứu (2.5).
2. **KDP trên cred**: **không có bằng chứng**; nhiều khả năng là lỗi offset (2.4). Cần 1 run nhánh cred với build mới.
3. **fscrypt/ENOKEY**: chưa có log chứng minh. Cần thu `umh_root_proof` + `dmesg` trong `handle_umh_mode`.
4. **`struct page`** (`0x30/0x20/0x18`): chưa đo; không ảnh hưởng hướng B.
5. **Panic đọc configfs** (ghostlockB14, `configfs_read_file→copy_to_user` từ `0x78`): có thật, **chưa rõ trigger** (nghi `page`/`pos` không nhất quán, hoặc `needs_read_fill!=0`). Cần xác nhận build mới có tái diễn không.

---

## 4. THÍ NGHIỆM TỐI THIỂU (phân định "chưa chắc")

**4.1 (đã làm — an toàn, không đụng máy) Chốt offset task_struct.**
Biên dịch lại `probe_offsets.c` với `-DCONFIG_CC_STACKPROTECTOR=1` rồi đọc `.rodata`:
```
pid 0x6A8 | tgid 0x6AC | comm 0x860 | cred 0x858 | real_cred 0x850 | tasks 0x5A8
prio 0xA8 | normal_prio 0xB0 | sched_task_group 0x400
pi_lock 0x924 | pi_waiters 0x930 | pi_top_task 0x940 | pi_blocked_on 0x948
mm 0x5F8 | real_parent 0x6B8 | atomic_flags 0x670 | seccomp 0x900 | sizeof 0xF80
fops: llseek 0x08 read 0x10 write 0x18 ioctl 0x48 mmap 0x58 open 0x60 release 0x70 splice 0xB8 show_fdinfo 0xD0
```
⇒ Khớp `offsets.h` (trừ `real_parent`, `seccomp`). **Hướng dẫn:** giữ bước này như một "golden check" mỗi lần đổi `out/.config`.

**4.2 (khuyến nghị) Phân định C3/2.4 — 1 run nhánh cred, build mới.**
```
adb push ghostlockB25_a64 → /data/local/tmp/a/e
ONLY_FOPS=1 SKIP_UMH=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_HOLD=0 \
SSOPT_OWNER0=0 PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=<slide> \
timeout 150 ./ghostlockB25  > gl.log 2>&1
```
Kỳ vọng:
- Nếu **không reset** và log có `root self=… comm=ll_root_child` ⇒ offset cred đúng, **KDP không chặn** ⇒ đóng câu hỏi C.
- Nếu **vẫn reset** ⇒ tìm dump theo process `ghostlockB25` (chờ 30–60 s), xem fault mới để phân biệt KDP vs bug khác.

**4.3 (khuyến nghị) Bắt trigger panic đọc configfs (câu hỏi §3.5).**
Thêm readback sau mỗi `configfs_read_once` (in `target`, `pos`, `page` ước lượng) rồi chạy `CFI_STOP_VERIFY=1`; nếu tái hiện `__arch_copy_to_user ≤ 0x100`, kiểm `needs_read_fill` có bị đặt lại 1 bởi `fill_write_buffer` không (`file.c:250`) khi fd trộn read/write.

---

## 5. PHỤ LỤC — bằng chứng trích dẫn

- `rtmutex.c`: `[7]` dequeue dòng 663-664; `rt_mutex_dequeue` 294-302; `rt_mutex_dequeue_pi` 327-335; `[11]` 715-747; vòng `retry` 585-589; `max_lock_depth` 474-490.
- `fops.c`: SSOPT_EMPTY 578-592; full payload 598-633; reset counters 644-645; peek 735-758; route_signal 767-776.
- `util.c`: `configfs_write_once` 1293-1310; `configfs_read_once` 1312-1330; `put_fake_fops_table` 359-377; `binwrite_target` 578; `fake_fops` 534.
- `fs/configfs/file.c`: `configfs_read_file` 115-134; `configfs_write_bin_file` 317-368; growth/vfree 335-361; struct 45-63.
- `drivers/staging/android/ashmem.c`: `struct ashmem_area` 54-60; prefix 37-39,265; `set_name` 539-568.
- `_dn_e2e6.log` (14/16 + reset); `_dn_e2e.log` (UMH 2×); `gl_QA_peek.log` (`cfi write ret=-1 errno=22`, target `selinux_state`).
- `kp_SCAN2.gz`/`kp_B14.gz` (B21 panic dòng 4282-4342); `kp_B18.gz` (B14 read-panic dòng 3034-3096); `kp_B18c.gz` (không Oops); `kp_cred.gz` (không Oops).
- Máy: `ro.product.model=SM-G970W`, `uname -r=4.14.190-23725627-abG970WVLU9IXE1`, `/proc/config.gz` (khớp `out/.config` trừ `CC_STACKPROTECTOR`).

## 6. TỰ KIỂM NGHIỆM BẢN AUDIT (vòng 2 — falsification)

Đã cố bác bỏ từng điểm yếu; kết quả:

| Điểm tự nghi | Cách kiểm | Kết quả |
|---|---|---|
| "+8 do canary" có thể sai (config khác còn chỗ khác) | Kéo lại `/proc/config.gz` của máy, **diff đầy đủ cả dòng `# ... is not set`** với `out/.config` | **Chỉ khác đúng nhóm `CC_STACKPROTECTOR`** (8 dòng). ⇒ kết luận +8 vững. |
| Offset probe có thể lệch do thứ tự mảng | Biên dịch lại `probe_offsets.c` + đọc lại `.rodata` với `CONFIG_CC_STACKPROTECTOR=1`; đối chiếu panic `[x19,#0x948]` | Khớp (`cred=0x858, comm=0x860, pi_blocked_on=0x948`). |
| "B18 reset do offset cred sai" (§2.4 nháp) | Tìm byte-pattern 3 offset trong binary B14/B18/B25 | **SAI** — B18/B25 đã đúng; chỉ B14 cũ. → đã đính chính §2.4. |
| `kp_SCAN2 == kp_B14` | `md5sum` | **Giống hệt** (`dd78c388…`) ⇒ xác nhận nhãn dump sai. |
| Dump e2e6 reset có Oops? | Quét toàn bộ `kp*.gz` theo process + dấu hiệu Oops | B18 (`kp_B18b`,`kp_B18c`) **không Oops** ⇒ reset im lặng (KDP-khả thi / hard-lockup). |
| `cfi write ret=35` có log thô? | grep toàn thư mục | **Không** — chỉ trong doc; log thô là `ret=8`/`ret=-1`. |
| `struct configfs_buffer` offset dựa disasm ELF (nhãn lệch) | — | Rủi ro: chuyển bằng chứng sang **thực nghiệm** (primitive chạy đúng) + layout struct + KPERFMON. |

**Còn điểm chưa kiểm được (giữ nguyên độ tin cậy thấp):**
- `struct page` `0x30/0x20/0x18` (không có probe; hướng B không dùng).
- Trigger panic đọc configfs (ghostlockB14, `__arch_copy_to_user VA=0x78`).
- Cơ chế UMH `complete=1` khi exec *thành công* (về lý thuyết `umh_complete` không chạy) — cần điều tra thêm (liên quan E2).

---

*Hết. Read-only; không đụng bootloader/partition/flash; không `adb uninstall`.*
