# KẾT LUẬN CHẶNG 3 — hybrid 64+32 đã chạy route, nhưng walk spin (2026-10-09)

> ⟶ Tài liệu lịch sử (chặng A→K). **Trạng thái mới nhất: `PHIEN_2026-10-10.md` §9**
> (nút thắt = nội dung sơn `waiter->tree_entry`, không phải hình học; ppoll bất khả thi;
> `CONFIG_SYSVIPC=n`). §K "Blocker còn lại" đã lỗi thời.

## A. Đã dựng được gì
- **Đọc panic trace không cần root**: `/data/log/dumpstate_lastkmsg_*.log.gz`
  (là ZIP; shell ở group `log`). Script: `analyze_lk.py`, `show_trace.py`, `show20.py`.
- **Route 32-bit (compat) chạy được**: `compat_sys_select` (nr 142) + fd_set 32-bit
  ⇒ `bits = SP0-0x1e0`, waiter `SP0-0x1b0` ⇒ **shift = 6** (task/lock ở ex word2/3
  = vùng user trực tiếp, select block được ⇒ paint không bị xoá).
- **Hybrid**: build armhf static (`build32.sh`, `-DCOMPAT32`), cha 64-bit làm
  leak KernelSnitch + spray, `fork+exec` con 32-bit `ghostlock32 --route <base> ...`;
  con chỉ chạy route; cha chạy `try_cfi_stage()` tiếp.
- Sửa arch cho 32-bit: `rdtsc`→`mrrc p15,1`, `sched_setattr` 274→**380**,
  `select`→`syscall(142,...)`, fd_set 2×32-bit; global địa chỉ route → `uint64_t`.
- Bug đã sửa: `strtoull(argv,0)` → base **16** (hex không tiền tố).

## B. Kết quả run hybrid (trace `kp20`)
```
Process ghostlock32 (32-bit)
rcu_sched self-detected stall  (soft lockup -> máy đơ, phải hard-reset)
Call trace:
 _raw_spin_unlock_irq+0x20
 rt_mutex_adjust_prio_chain+0x1dc   <-- nhánh retry (trylock waiter->lock->wait_lock FAIL)
 remove_waiter+0x19c
 rt_mutex_cleanup_proxy_lock+0x50
 futex_lock_pi+0x6c0
 do_futex+0xbb0
 compat_SyS_futex+0x108             <-- đúng ABI 32-bit
```

Diễn giải:
- Con 32-bit THẬT SỰ chạy route (compat futex), khác hẳn native.
- Hỏng đổi từ "crash `trylock` với `lock=0`" (native) → "**spin retry** vì trylock
  `lock->wait_lock` fail" (32-bit). ⇒ overlay shift=6 **đã thay đổi trạng thái**.
- Walk bị kích bởi **chính futex setup của exploit** (`futex_lock_pi`→`remove_waiter`),
  không phải consumer `sched_setattr`.

## C. Việc kế tiếp (khi tiếp tục)
1. Thêm log riêng + `fsync` cho con 32-bit (base/fake_lock/fake_task/route progress)
   để xác nhận overlay vào đúng chỗ (log gl38 bị cắt do hang).
2. Vì sao `trylock(waiter->lock->wait_lock)` fail: kiểm `waiter->lock` trong walk này
   là fake_lock hay lock thật (kích bởi futex setup), và thứ tự/thời điểm overlay.
3. `gl38.log` dừng trong KernelSnitch của cha (dù trace là con) → cần tách log 2 tiến trình.

## D. Cảnh báo
Walk spin = **soft lockup ⇒ máy ĐƠ, phải hard-reset** (khó chịu hơn panic).
Mỗi lần thử sai có thể phải reset tay.

## E. CHẶNG 4 — bug offset `pi_*` (+8) + trạng thái mới
**Bug thật (disasm xác nhận, KHÔNG phải suy):** task_struct 4.14 của máy có
```
pi_lock=0x924  pi_waiters=0x930  pi_top_task=0x940  pi_blocked_on=0x948
```
(rt_mutex_adjust_pi: `add x20,x0,#0x924`, `ldr x8,[x19,#2376]`;
 task_blocks_on_rt_mutex: `add x24,xN,#0x924`, `add x1,xN,#0x930`.)
Nhưng bảng `beyond0q/offsets.h` ghi `0x91C/0x928/0x938/0x940` → **lệch +8**.
→ đã sửa bảng. (fake_task trước đây đặt `pi_waiters` sai 8 byte.)

**Sau fix**, chạy lại hybrid:
- Con 32-bit chạy đúng: `route child base=ffffffc0395f8000 lock=... w0=...+300
  task=...+400 fops=...+100` (giá trị 64-bit đúng; dòng "route setup" in sai do
  format `%zx` vs uint64_t — chỉ là log).
- Overlay shift=6 đặt `task`@ex word2, `lock`@ex word3 (đúng chỗ waiter+0x30/+0x38
  khi `bits=SP0-0x1e0`).
- Nhưng trace `_23`: crash `lock=0` tại `raw_spin_trylock(&lock->wait_lock)`,
  vào từ `futex_lock_pi → rt_mutex_cleanup_proxy_lock → remove_waiter →
  adjust_prio_chain` — tức walk theo **`owner->pi_blocked_on`**, KHÔNG phải waiter
  trên stack luồng waiter (chỗ select đã sơn) ⇒ `lock=0`.
- ⇒ Nghi vấn mới: route của exploit kích `remove_waiter` ở **nhánh `futex_lock_pi`
  (owner)**, không đúng nhánh requeue mà overlay nhắm tới.

**Việc kế tiếp:** làm rõ route sequencing (luồng nào dính `remove_waiter`), và/hoặc
sơn đúng waiter của luồng owner — thay vì luồng waiter.

## F. CHẶNG 5 — route sequencing (log đầy đủ) + công cụ quét syscall
**Thứ tự route (con 32-bit, `rchild.log` O_SYNC):**
```
owner: target_lock ret=0
waiter: chain_lock ret=0
owner: chain_lock_enter            (owner LOCK_PI(f_pi_chain) block; KHÔNG có ret)
waiter: wrp_enter
main: cmp_requeue ret=-1 errno=35  (EDEADLK → bug ĐÃ kích)
waiter: wrp_ret ret=-1 errno=110   (ETIMEDOUT → waiter KHÔNG được requeue)
pselect route setup ... shift=6
pselect pre-select +5ms
<crash>
```
→ Bug kích ✓ nhưng **waiter không được requeue** (timeout). Crash là một
`FUTEX_LOCK_PI` thất bại→`cleanup_proxy_lock→remove_waiter→adjust_prio_chain`
(4.14: `futex_lock_pi` dòng 3034 / `futex_wait_requeue_pi` dòng 3441), walk trên
**task của `remove_waiter`** (owner) ⇒ `lock=0`.

**Công cụ quét syscall (offline, thuần disasm):** `geom_scan3.py` (memoize+8 luồng,
1m13s, 394 entry 32+64-bit) + `analyze_one.py` + `filter_geom.py`.
- Không syscall nào có copy **độ dài cố định** phủ waiter; mọi copy đủ sâu đều **L động**.
- Điều kiện phủ: `X_s ≥ 0x180` và `L ≥ X_s-0x178`.
- **Ứng viên copy THÔ:** `SyS_setsockopt` (optname=1000, buffer 256B tại `SP0-0x1f0`,
  `L=min(optlen,254)` ⇒ optlen=0x80 phủ được; không cần quyền, không block);
  `SyS_ptrace` (`SP0-0x18e`, cần L≥0x16, **block được**); `compat_SyS_signalfd` 0x1e6.
- **Loại:** `sendmsg`(iovstack)/`io_submit`/`vmsplice`/`process_vm_*` = validated;
  `send`/`socketcall` (sockaddr ≤128); `reboot`/`quotactl` (quyền).

## G. CHẶNG 6 — SỬA GỐC RỄ: walk ĐÚNG luồng, sai ở PAINT (kp24)

**Bác bỏ giả thuyết (b) cũ.** Trace mới nhất `kp24` (lần chạy ghostlock40) cho:
```
Call trace:
 _raw_spin_trylock+0x1c/0x80
 rt_mutex_adjust_prio_chain+0x244/0x830
 rt_mutex_adjust_pi+0xa0/0xb8
 __sched_setscheduler+0x890/0xab0
 SyS_sched_setattr+0x2c8/0x358
```
⇒ Walk **KHÔNG phải** từ `futex_lock_pi`/`remove_waiter` (trace `_23` cũ), mà đúng
đường dự định: `sched_setattr(target=T) → rt_mutex_adjust_pi(T) → adjust_prio_chain`.
`task` = **luồng waiter** (T) — tức walk chạy **đúng luồng**, không phải owner.
Vậy "(b) walk sai luồng" là **sai**; vấn đề còn lại là **paint không vào `lock`**.

**Địa chỉ & offset xác nhận (Image base `0xffffff8008000000`, KASLR slide `0x2500000`):**
- `_raw_spin_trylock` link `0xffffff80096f99c4` (byte-pattern khớp file offset → base đúng).
- `+0x244` = ngay sau `bl _raw_spin_trylock` tại `+0x240`; tham số `x0 = x24`.
- Ngay trước đó: `ldr x25,[x19,#0x948]` = `task->pi_blocked_on`, `ldr x8,[x25,#0x38]`
  = `waiter->lock`, `cmp x24,x8` ⇒ `x24 = waiter->lock`. Crash `x24=0` ⇒ **`waiter->lock == 0`**.
- `rt_mutex_adjust_pi`: `add x20,x0,#0x924` = `raw_spin_lock(&task->pi_lock)` ⇒
  `pi_lock=0x924`, `pi_blocked_on=0x948` **khớp** bảng beyond0q.
- `task_blocks_on_rt_mutex`: `stp x20,x19,[x21,#48]` ⇒ **`waiter->task=0x30`,
  `waiter->lock=0x38`**, `+0x40`=prio, `+0x48`=deadline.

**Hình học stack (từ chính kernel device):**
- `compat_SyS_select`: `sub sp,#0x70`; `compat_core_sys_select`: `sub sp,#0x1c0`,
  `stack_fds` (=`bits`) tại `sp+0x50` ⇒ **bits = SP0-0x1e0**.
- `compat_SyS_futex`: `sub sp,#0x70`; `do_futex` (đã inline `futex_wait_requeue_pi`):
  `stp [sp,#-96]!` + `sub sp,#0x1b0`, `rt_waiter` tại `sp+0xd0` ⇒ **waiter = SP0-0x1b0**.
- `waiter - bits = 0x30` ⇒ **shift = 6** ✓. `task` @ waiter+0x30 = bits+0x60 = word 12
  = **ex word2**; `lock` @ waiter+0x38 = bits+0x68 = **ex word3** ⇒ bảng `words_compact`
  (task word6, lock word7) **đúng**.

**BUG GỐC RỄ:** `pselect_words_per_set()` dùng `8*sizeof(unsigned long)` — trong build
armhf `sizeof(unsigned long)==4` ⇒ `(320+31)/32 = 10` (phải là 5). Nhưng kernel
`compat_core_sys_select` luôn dùng long 64-bit: `size = FDS_LONGS(n)*8`,
`FDS_LONGS=(n+63)/64` (đã đọc disasm: `add x8,x22,#0x3f; lsr x25,x8,#6`). ⇒ mọi field
bị đặt **lệch 5 long (0x28)**, `task`/`lock` rơi vào `out word2/3` (= bits+0x38/0x40,
tức waiter+0x08/+0x10), còn `waiter->lock` (bits+0x68) **không bao giờ được sơn** ⇒
`lock=0` ⇒ crash.

**Đã sửa:** `pselect_words_per_set()` và `slide_pselect_words_per_set()` → `(nfds+63)/64`
(64-bit words cho cả hai build). Rebuild `ghostlock42`.

**Việc kế tiếp:** chạy lại `ghostlock42` (child đã sửa) — kỳ vọng `waiter->lock` =
`fake_lock` (≠0) ⇒ crash đổi sang địa chỉ khác (PAN/đọc trang spray), hoặc qua được
walk. Nếu đúng ⇒ chuyển sang leak KASLR (slide) → CFI/physrw → root.

## H. CHẶNG 7 — thay `pselect` bằng `setsockopt` (offset HẰNG)

**Lý do:** route `select` "lòng vòng" — phải đoán `shift`, 32-bit compat, bitmap
32↔64, `res_*` bị zero. `setsockopt` cho buffer stack **offset cố định** ⇒ dễ đối chiếu.

**Kiểm chứng (disasm máy, base `0xffffff8008000000`):**
- `SyS_setsockopt` (`=sys_setsockopt`) `stp x29,x16,[sp,#-80]!` ⇒ frame **0x50**;
  chỉ vào `sock_setsockopt` khi `level==SOL_SOCKET(1)` (`cmp w25,#1`).
- `sock_setsockopt` `sub sp,sp,#0x180`, buffer `sp+0x10` ⇒ **buf = SP0-0x1c0**.
- Nhánh `optname==0x3e8 (1000)`:
  `add x0,sp,#0x10 ; bl memset(buf,0,0xff) ; csel len=min(optlen,0xfe) ;
   bl __arch_copy_from_user(buf,optval,len)` — copy **trước** khi xử lý, **không cần quyền**.
- `SyS_futex` (native) `sub sp,#0x70` = compat ⇒ **waiter = SP0-0x1b0 cho cả native**.
- `rt_mutex_waiter`: `task@+0x30`, `lock@+0x38` (từ `task_blocks_on_rt_mutex`).
- ⇒ **`task` = buf[0x40], `lock` = buf[0x48]** (option len ≥ 0x50).
- Sửa luôn bug scan: `analyze_one.py` đọc `[sp,#-80]!` rồi `int('80',16)` = 0x80
  (đúng 80) ⇒ nó báo `SP0-0x1f0` trong khi thật là `SP0-0x1c0`.

**Cảnh báo (đã đo):** `setsockopt` KHÔNG block. Đường thoát `do_notify_resume`
(frame `0x190`, chỉ chạy khi `TIF_SIGPENDING/TIF_NOTIFY_RESUME`) ghi:
`[sp+8]→SP0-0x188`, `[sp+0x10]→SP0-0x180 (task!)`, `[sp+40]→SP0-0x168 (deadline)`,
`[sp+48]→SP0-0x160` — **KHÔNG** đụng `lock` (`SP0-0x178`). Nên `lock` an toàn;
`task` có thể bị đè (route đã tắt rseq nên thường không có flag ⇒ có thể không chạy).

**Đã code:** `fops.c::do_setsockopt_fake_lock_route()` (dispatch qua env
`ROUTE_SETSOCKOPT=1` trong `waiter_thread`); build `ghostlock43` (a64 + arm32).
Chạy native standalone: `ROUTE_SETSOCKOPT=1 ./ghostlock43 --route <base> <t> <v> 4`.
Kỳ vọng: fault đổi từ `x0=0` sang `fake_lock` ⇒ paint TRÚNG.

### H.1 KẾT QUẢ (✅ TRÚNG)
- Lần chạy `ghostlock44`, `--route ffffffc800000000 ...` (địa chỉ chưa map):
  ```
  Unable to handle kernel paging request at virtual address ffffffc800000000
  pc  : _raw_spin_trylock+0x1c
  lr  : rt_mutex_adjust_prio_chain+0x244
  x24 : ffffffc800000000   (= waiter->lock = fake_lock)
  x0  : ffffffc800000000   (= &lock->wait_lock)
  x25 : ffffff8021f6bd10   (= waiter, trên stack T)
  x19 : ffffffc182ec0f80   (= task = T)
  ```
  ⇒ `sched_setattr(T) → rt_mutex_adjust_pi → task->pi_blocked_on (waiter giả) →
  lock = waiter->lock → raw_spin_trylock(lock->wait_lock)` — **paint trúng byte**.
- **Nguyên nhân "trượt" ban đầu = RACE thứ tự**, không phải sai offset: consumer
  bắn khi `sock_setsockopt` chưa copy xong (bằng chứng: lần chạy sau đọc được giá
  trị `fake_lock` của lần chạy TRƯỚC — vì page kernel-stack được tái chế theo trang
  vật lý). Sửa: đặt `punch_consume_go` **sau** khi `setsockopt` trả về + `usleep(20ms)`.
- ⇒ Từ đây route native 64-bit + `setsockopt` là **đường chính**; `select`/`shift`/compat
  bỏ được.

**Việc kế tiếp:** cấp **trang giả hợp lệ** tại `fake_lock` (spray của cha) để walk đi
qua `trylock` và tới thao tác rb-tree (**PI write**) — tức tích hợp route mới vào flow
đầy đủ (cha 64-bit spray, con 64-bit chạy route) và mở khoá bước CFI/configfs.

## I. CHẶNG 8 — KHẢO SÁT STARUCT (không đoán) + 3 FIX

Đối chiếu TỪNG struct với kernel 4.14 của máy (nguồn: `rtmutex_common.h`,
`include/linux/fs.h`, disasm `rt_mutex_adjust_pi`/`pipe_read`/`configfs_read_bin_file`,
kallsyms):

**Layout thật (khớp):**
- `rt_mutex_waiter`: `tree@0x00`, **`pi_tree@0x18`**, `task@0x30`, `lock@0x38`,
  `prio@0x40`, `deadline@0x48` (disasm `ldr x8,[x25,#24]!` = waiter+0x18).
- `rt_mutex`: `wait_lock@0`, `waiters.rb_root@0x08`, `rb_leftmost@0x10`, `owner@0x18` ✓.
- `file_operations` (11 field) ✓ bảng beyond0q khớp `include/linux/fs.h`.
- `configfs_buffer`: `page@0x10 … needs_read_fill@0x50, bin_buffer@0x58, size@0x60` ✓.
- `cred`: uid@4, securebits@0x24, caps@0x28, security@0x78 ✓.
- Symbol offset khớp 100%: `noop_llseek`, `configfs_read_bin_file`,
  `configfs_write_bin_file`, `cap_capable`, `ashmem_*`.

**3 lỗi (hằng 6.x/5.x chưa port):**
1. ⭐ `off_ashmem_misc_fops` (bảng beyond0q) = **0x02BB1750** = `&ashmem_misc` (base struct),
   nhưng `.fops` ở **base+0x10 = 0x02BB1760** (kallsyms `ashmem_misc` = base). `main.c:62`
   override `ASHMEM_MISC_FOPS_OFF` bằng giá trị bảng ⇒ **ghi `fake_fops` vào field `minor`**
   chứ không phải `.fops` ⇒ **redirect fops không xảy ra** ⇒ `cfi write EINVAL`.
   → Sửa bảng: `0x02BB1760`.
2. `FAKE_WAITER_PI_TREE_ENTRY_OFF` = 0x28 (6.x) → **0x18**: node ghi `rb_set_parent` bị
   lệch 0x10, `write_right/left` đè `task`/`lock`.
3. `FAKE_TASK_USAGE_OFF` = 0x40 (6.x) → **0x68** (disasm inline `get_task_struct`):
   `get/put_task_struct(fake_task)` sai field ⇒ `put` có thể chạm 0 ⇒ free nhầm.

**Đã sửa (per-device, đúng pattern RSO):**
- `devices/offsets.h`: thêm `waiter_pi_tree_off`, `task_usage_off`.
- `devices/beyond0q/offsets.h`: `.off_ashmem_misc_fops = 0x02BB1760`,
  `.waiter_pi_tree_off = 0x18, .task_usage_off = 0x68`.
- `core/runtime_struct_offsets.h`: `FAKE_WAITER_PI_TREE_ENTRY_OFF`/`FAKE_TASK_USAGE_OFF`
  thành `_RSO(...)` (mặc định 6.x giữ nguyên).

**Còn nợ (bước sau):** `PIPE_TMP_PAGE_OFF/BUFS_OFF/USER_OFF/SIZE` trong `target.h` là 5.x;
4.14 thật `tmp_page@0x68, bufs@0x80, user@0x88, sizeof~0x90`.

**Việc kế tiếp:** chạy full flow với 3 fix (`ghostlock49`) — kỳ vọng walk hoàn tất PI
write (ghi `fake_fops` vào `.fops`) rồi CFI stage chạy.

### I.1 LỖI #4 — paint bị ĐÈ bởi syscall sâu sau nó (chặng 8b)

Full flow với 3 fix vẫn panic ở `trylock` với `x24` = rác (không phải `fake_lock`).
Truy ra: **paint của `setsockopt` nằm NÔNG** (`buf = SP0-0x1c0`, phủ `SP0-0x1c0..0x160`),
nên **bất kỳ syscall sâu nào chạy sau nó đều đè mất**:
- `nanosleep`: `SyS_nanosleep(0xb0)+hrtimer_nanosleep(0xa0)+do_nanosleep(0x60)=0x1b0`
  ⇒ frame phủ `SP0-0x1b0..SP0` ⇒ đè `task@-0x180`, `lock@-0x178`.
- **`pr_info` log sau paint** (write xuống file O_SYNC → ext4) còn sâu hơn.

Điều này giải thích: **standalone `ghostlock44` trúng (kp27)** vì nó spin-park trong
userspace và **không log sau paint**; còn các bản thêm log/nanosleep thì `lock` = rác.

**Cơ chế gốc** (chọn `select`): vùng paint do **chính frame của syscall** dựng
(`bits@SP0-0x1e0`), rồi block ở **sâu hơn** (`do_select`) nên paint không bị chạm —
đó là lý do gốc cần một syscall *vừa ghi stack vừa block*.

**Đã sửa:** (1) **spin-park userspace** (không syscall giữa paint và walk, như standalone);
(2) **gate log sau paint** bằng `SSOPT_LOG` (mặc định tắt). Build `ghostlock52`.

**Việc kế tiếp:** chạy `ghostlock52` — kỳ vọng `x24 = fake_lock` (không rác) và walk đi
hết (dùng pi_tree 0x18 + usage 0x68) tới PI write ⇒ CFI stage.

## J. CHẶNG 9 — BỎ CƠ CHẾ CHA–CON (theo repo gốc)

**Audit:** cùng binary `ghostlock52`, **standalone `--route` paint TRÚNG** đúng
`buf[0x48]` (`x24 = 0x1a2b00000048` = giá trị scan cho slot 0x48, `kp38`), nhưng
**full flow `fork/exec` con thì trượt** ⇒ hình học đúng, khác biệt nằm ở **đường
tiến trình** (cha spray + `fork/exec`).

**Nguồn gốc cha–con:** chỉ có từ thời route `select` 32-bit compat (cần tiến trình
armhf để có `shift=6` + syscall compat nr 142). Khi chuyển sang `setsockopt`
(offset hằng, native là đủ) thì con 32-bit **thừa**, nhưng `do_one_write` chỉ đổi
đường dẫn con sang binary 64-bit chứ không bỏ `fork/exec`.

**Đã sửa:** `do_one_write` trở về **1 tiến trình như bản gốc**:
```
spray (prepare_good_kernel_page) → run_main_route_threads()
route tự gọi try_cfi_stage() (route_only_mode == 0)   [bỏ hẳn fork/exec]
```
Build `ghostlock53`. (Đường `--route`/`run_route_only` vẫn giữ để test standalone.)

**Việc kế tiếp:** chạy `ghostlock53` — nếu paint trúng (như standalone) và walk đi hết
thì ta đã qua bước PI write và tới CFI stage.

### J.1 GỐC RỄ TÌM ĐƯỢC — 4096 thread futex KernelSnitch để lại (chặng 9b)

Audit `kernelsnitch.h`:
- `__increase(ks, ID=128, APPENDED_FUTEXES=4096)` → tạo **4096 thread**, mỗi thread
  `FUTEX_WAIT_PRIVATE(&ks->inc_futex[128], 0, NULL)` **block vĩnh viễn**; **không join,
  không detach**.
- `kernelsnitch_cleanup()` **chỉ `munmap`** (`ks->times/tids/futex_addrs/futexes/ks`),
  **không wake/cancel/join** ⇒ 4096 thread treo ở futex-wait vẫn sống khi route chạy.
- Chúng thừa hưởng **affinity `CORE`** của tiến trình ⇒ **4096 thread dồn 1 core** ⇒
  làm lệch mạnh timing/trạng thái so với standalone (standalone **không chạy KernelSnitch**).

**Sửa:** trong `__do_increase` thêm `pthread_detach(pthread_self())`; trong
`kernelsnitch_cleanup` **`FUTEX_WAKE(inc_futex[128], INT_MAX)` + `sched_yield`**
**trước** `munmap` để 4096 thread thoát. Build `ghostlock54`.

**XÁC NHẬN (kp41):** full flow + `SSOPT_SCAN=1` → **`x24 = 0x1a2b00000048`** = đúng slot
`buf[0x48]` ⇒ **paint TRÚNG trong full flow** (trước đó trượt). ⇒ Gốc rễ là **4096
thread futex để lại**, không phải hình học/`fork/exec`/spray-page.

**Việc kế tiếp:** chạy `ghostlock54` không scan — `waiter->lock = fake_lock` (trang spray)
⇒ walk kỳ vọng qua `trylock` và chạy PI write ⇒ `try_cfi_stage()`.

## K. CHỐT PHIÊN — trạng thái & việc mở

**Đã đạt (phiên này):**
1. **Route `setsockopt`** thay `select`: offset HẰNG (`task@buf[0x40]`, `lock@buf[0x48]`),
   bỏ `shift`/ABI 32-bit/`res_*`. Xác nhận paint trúng (`x24 = 0x1a2b00000048`, `kp41`).
2. **3 lỗi port hằng số** (suy từ source/disasm, không đoán):
   `off_ashmem_misc_fops 0x2BB1750→0x2BB1760` (field `.fops`, +0x10);
   `FAKE_WAITER_PI_TREE_ENTRY_OFF 0x28→0x18`;
   `FAKE_TASK_USAGE_OFF 0x40→0x68` (RSO per-device).
3. **Gốc rễ paint trượt trong full flow**: KernelSnitch để lại **4096 thread**
   (`__increase(APPENDED_FUTEXES=4096)`, block futex, không join/detach) mà
   `kernelsnitch_cleanup` chỉ `munmap`. Sửa: `pthread_detach` trong `__do_increase`
   + **`FUTEX_WAKE` lặp** trước `munmap`.
4. **Bỏ cơ chế cha–con** (`do_one_write` → 1 tiến trình như repo gốc).
5. **Audit skb**: `SKB_MAX_HEAD(0)=0xE80` suy từ `sizeof(skb_shared_info)=0x150`(có KNOX_VPN)
   ⇒ `LOCK_OFF=0xE80`/`SKB_DATA_DELTA=-0xE80` **đúng**, không phải lỗi hằng.

**Blocker còn lại:** reclaim **không đặt fake-page vào `base`** — kp43: `[base+0x10]=0`
(đáng lẽ `fake_w0`). Nghi:
- KernelSnitch leak **`current->mm`** (mm của chính exploit) ⇒ trang order-3 **không free được**;
- `kill_child(prepare_ctx.childs)` chạy **SAU** reclaim `sendmsg` ⇒ slab chưa free lúc reclaim.
- (CPU ok: free và sendmsg cùng `CORE`.)

**File/tham chiếu:** `HANDOFF.md`, `TONG_QUAN.md`, `AUDIT_GEOMETRY.md`, file này.
Binary cuối: `ghostlock52`(đo paint), `ghostlock55`(wake-loop).
