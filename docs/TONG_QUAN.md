# TỔNG QUAN — GhostLock (CVE-2026-43499) và port sang Galaxy S10e / 4.14.190

> ⟶ Bản mô tả tổng quan (để thảo luận). **Trạng thái/đường ra mới nhất: `BAN_GIAO.md` §12 và
> `PHIEN_2026-10-10.md` §9** (nút thắt = sơn `waiter->tree_entry`; `ppoll` bất khả thi;
> `CONFIG_SYSVIPC=n`; không cần syscall block).

Mục tiêu: root **SM-G970W (Snapdragon 855, kernel 4.14.190, bootloader khoá cứng)**
bằng GhostLock — không mở bootloader, không sửa boot image.
Exploit nguồn: `JoinChang/ghostlock-oneplus`. Bản này là bản mô tả để thảo luận.

---

## 1. Lỗ hổng — futex PI Use-After-Free

Bug nằm ở `remove_waiter()` (kernel/locking/rtmutex.c).

- Khi một thread block trên **PI-futex**, kernel dựng một `struct rt_mutex_waiter`
  **ngay trên kernel stack** của thread đó (waiter "sống" trong frame hàm).
- `remove_waiter(lock, waiter)` lẽ ra phải xoá con trỏ của **chủ waiter**:

  ```
  waiter->task->pi_blocked_on = NULL      // ĐÚNG
  ```

- Nhưng bản lỗi xoá của **thread đang gọi**:

  ```
  current->pi_blocked_on = NULL           // LỖI
  ```

- Nếu `current != waiter->task` (đúng trong nhánh **requeue-PI** và **deadlock**),
  thì `waiter->task` **vẫn còn `pi_blocked_on` trỏ vào waiter đã bị gỡ khỏi hàng đợi**
  → **con trỏ treo** vào một vùng **kernel stack đã chết**.

Ba bước khai thác:

1. **Tạo waiter + kích bug** → một task còn `pi_blocked_on` trỏ vào vùng stack cũ.
2. **Tái chiếm vùng stack đó** bằng một syscall khác (`pselect6`/`select`): bitmaps
   `fd_set` do người dùng đưa lên được copy vào `stack_fds` trên kernel stack, ghi đè
   đúng vị trí `rt_mutex_waiter` → tạo **waiter giả** (điều khiển `task`, `lock`,
   `prio`, `deadline`).
3. **Kích `rt_mutex_adjust_pi(task)`** (đổi priority task, ví dụ `sched_setattr`).
   Kernel walk chuỗi PI: đọc `task->pi_blocked_on` (nay là waiter giả) →
   `lock = waiter->lock` → thao tác **rb-tree rebalance** trên `lock->waiters`
   (trang giả) → **ghi giá trị có kiểm soát vào địa chỉ có kiểm soát**. Đó là "PI write".

> README nguồn nói CVE ảnh hưởng **Linux 5.7–7.1**; nhưng code `remove_waiter` lỗi này
> **có mặt cả ở 4.14** (đã kiểm tra source máy) ⇒ cùng nguyên lý, khác hình học stack.

---

## 2. Vì sao `select` tái chiếm được — ràng buộc "feasibility"

`core_sys_select` (NFDS=320) cấp **256 byte `stack_fds`** trên kernel stack:

```
stack_fds:  0    5    10   14 | 15    20    25   29   (word, 64-bit)
            ├─in─┤─out─┤─ex──┤ ├res_in┤res_out┤res_ex┤
            ◄── NGƯỜI DÙNG GHI ĐƯỢC ──► │ ◄── kernel tự zero ──►
```

- Nửa đầu (`in/out/ex`) là **kernel copy từ bitmap người dùng** ⇒ sửa được.
- Nửa sau (`res_*`) bị `zero_fd_set()` xoá ⇒ **không** đặt giá trị trực tiếp được
  (muốn "đặt res_*" thì phải làm cho fd tương ứng ready để `do_select` tính ra).

⇒ Waiter treo **phải rơi vào nửa đầu**. Waiter rơi ở word nào là do **độ sâu call-chain**
(`sys_futex → do_futex → futex_wait_requeue_pi`), tức do compiler/PGO — **không** do version.

- `do_futex` bị **PGO inline** (OnePlus 6.1, X9 Ultra 6.12.69, …) → waiter rơi quá sâu
  (word 13–24) → **bất khả thi**.
- Chain chuẩn → waiter word = 2 (6.12/6.6), 3 (6.1 vivo), 0 (5.10 OPLUS)…

`PSELECT_SHIFT` = vị trí tương đối waiter so với `bits` (0, −2 tuỳ máy).

---

## 3. Repo gốc `ghostlock-oneplus` — hai đường root

### Path A — UMH Root (ưu tiên, thiết bị "C ashmem")

Điều kiện: `off_ashmem_misc_fops != 0` (ashmem tĩnh trong BSS — 5.10/6.1/OnePlus 13).

```
PI write (mode=4)  → redirect miscdevice.fops → fake fops (CFI stage)
                   → configfs read/write
                   → pipe physrw (đọc/ghi kernel chính xác 1 byte)
                   → tắt SELinux (1 byte, không phá policycap)
                   → UMH: chèn work_struct vào system_unbound_wq
                   → script root → ksud late-load → cài KernelSU
```

Không dùng được với "Rust ashmem" (6.12 GKI — miscdevice cấp phát trên heap).

### Path B — Direct PI Write (dự phòng)

```
Write 1 (mode=1)  → selinux_enforcing = 0    (ghi 8 byte, phá byte kề)
Write 2 (mode=2)  → task->cred = init_cred   (uid=0 + full caps)
→ root shell → ksud late-load → KernelSU
→ vá policy SELinux (config |= 0xC0000000) rồi load lại để khôi phục mạng
```

### Bootstrap mode (điện thoại chạy độc lập)

```
app (seccomp) → Write 1 → mini-adb TCP → adb shell: chạy full exploit → root
```

### Bản đồ file

| File | Vai trò |
|---|---|
| `main.c` | Entry, W1/W2, UMH path, bootstrap, root script, vá policy SELinux |
| `fops.c` | **pselect route, PI write, CFI stage**, compact waiter |
| `util.c` | Heap spray (skb), KernelSnitch, slab drain, dựng payload/trang giả |
| `slide.c` | Leak **KASLR base** (qua `boot_id`/`nfulnl_logger`) |
| `pipe_physrw.c` | `struct pipe_inode_info` → đọc/ghi **physical memory** |
| `umh_root.c` | UMH root bằng inject `work_struct` vào workqueue |
| `miniadb.c` | Mini ADB client (bootstrap) |
| `target.h` | Layout bộ nhớ + offset struct mặc định |
| `runtime_struct_offsets.h` | Override offset struct theo thiết bị |
| `devices/offsets.h` | Bảng offset theo `uname -r` + macro `STRUCT_OFFSETS_*` |

### Các tham số phụ thuộc máy

- **`kernel_phys_load`** (bootloader chọn): SM8845/8750/8650 = `0xa8000000`,
  SM8850 = `0xc7800000`. Sai ⇒ hỏng âm thầm. Đọc: `grep "Kernel code" /proc/iomem`
  (cần root) hoặc `KPHYS=` override.
- **`KIMAGE_TEXT_BASE`**: 5.10 = `0xffffffc008000000`, 6.x = `0xffffffc080000000`.
- **Waiter layout**: 6.12/6.6 = *nested* (14 word), 6.1/5.10 = *compact* (10 word).

---

## 4. Port sang 4.14.190 — khác biệt so với repo gốc

| Vấn đề | Repo gốc (6.x) | Port 4.14 của ta |
|---|---|---|
| Route chính | `pselect6` (64-bit) | **compat `select` (nr 142, 32-bit)** — vì đường native bị `do_notify_resume` ghi đè khi trả syscall |
| Tiến trình | 1 process aarch64 | **hybrid**: cha 64-bit (leak/spray/CFI) + con 32-bit (`--route`, chỉ chạy select) |
| VA_BITS | 39 | 39 (`PAGE_OFFSET=0xffffffc000000000`, `KIMAGE_TEXT_BASE=0xffffff8008000000`) |
| Waiter layout | nested 14 word | **compact**: `pi_tree@0x18`, `task@0x30`, `lock@0x38`, `prio@0x40`, `deadline@0x48` |
| Offset struct | theo BTF | theo source 4.14 (probe offsetof) + bảng `beyond0q/offsets.h` |

### Hình học đã đo **từ chính kernel máy** (không tune mù)

Base Image `0xffffff8008000000` (đã verify bằng byte-pattern), KASLR slide `0x2500000`.

- `compat_SyS_select` (`sub sp,#0x70`) → `compat_core_sys_select` (`sub sp,#0x1c0`,
  `stack_fds` tại `sp+0x50`) ⇒ **`bits = SP0-0x1e0`**.
- `compat_SyS_futex` (`sub sp,#0x70`) → `do_futex` (`sub sp,#0x210`, `rt_waiter`= `sp+0xd0`)
  ⇒ **`waiter = SP0-0x1b0`**.
- `waiter - bits = 0x30` ⇒ **SHIFT = 6**.
- `task` @ `waiter+0x30` = `bits+0x60` = **ex word2**;
  `lock` @ `waiter+0x38` = `bits+0x68` = **ex word3**.
- Kernel `compat_core_sys_select` dùng long 64-bit: `size = ((n+63)/64)*8` ⇒ **5 word/set**.

### Bug đã tìm & sửa

`pselect_words_per_set()` (và `slide_pselect_words_per_set()`) tính
`8*sizeof(unsigned long)` — trong build **armhf `sizeof(unsigned long)==4`** ⇒ trả **10**
thay vì **5** ⇒ mọi field bị đặt **lệch 5 long (0x28)**, `task`/`lock` rơi vào
`out word2/3` thay vì `ex word2/3`. **Đã sửa** về `(nfds+63)/64` (word 64-bit cho cả 2 build).

---

## 5. Trạng thái hiện tại (để thảo luận)

Đã có:
- Trigger bug ✓ (`CMP_REQUEUE_PI` → `EDEADLK`).
- Route 32-bit chạy ✓, hình học xác nhận ✓, waiter compact xác nhận ✓.
- Trace `kp24`/`kp25` cho **đúng đường dự định**:

  ```
  _raw_spin_trylock+0x1c
  rt_mutex_adjust_prio_chain+0x244     ← x0 = x24 = waiter->lock = 0
  rt_mutex_adjust_pi+0xa0
  __sched_setscheduler+0x890
  SyS_sched_setattr+0x2c8
  ```

  ⇒ Walk chạy trên **đúng luồng waiter** (`sched_setattr → rt_mutex_adjust_pi(T)`).
  Giả thiết cũ "(b) walk sai luồng (owner)" là **SAI**.

**Vấn đề còn lại:** `waiter->lock` đọc ra `0` ⇒ **paint chưa vào `lock`**.

**Giả thuyết đang nghi (cần thảo luận/bác bỏ):**
- Trong nhánh **requeue** (CMP_REQUEUE_PI), waiter treo có thể nằm trong frame của
  **`futex_requeue()` (thread MAIN)**, chứ không phải frame của thread chạy `select`
  → paint sơn nhầm thread ⇒ `lock` vẫn là giá trị cũ/0.
- Hoặc: vùng waiter bị ghi đè sau paint (vd. bởi vùng `res_*` bị zero, hoặc bởi
  chính frame `select` của một call khác).
- Hoặc: `n` bị chặn bởi `max_fds` ⇒ `ex word3` không được copy.

**Bước kiểm chứng đề xuất (0–1 reboot):**
1. Xác định **waiter treo nằm trên stack của thread nào** (main vs waiter) — bằng cách
   truy `task_blocks_on_rt_mutex` được gọi từ `futex_requeue` (main) và so `rt_waiter`
   arg (con trỏ stack) với `task->pi_blocked_on` trên trace.
2. Nếu là main: cho **thread đúng** chạy overlay `select` (hoặc để main tự chạy select).
3. Nếu vẫn 0: kiểm `max_fds` (log `n` sau khi cap) và xác nhận `ex word3` được copy.

**Sau khi paint ăn:** còn lại cả chuỗi — leak KASLR (`slide`) → CFI/configfs →
pipe physrw → tắt SELinux → root (hoặc UMH).

---

## 6. Tài liệu/nguồn trong workspace

| File | Nội dung |
|---|---|
| `TONG_QUAN.md` | Bản này |
| `HANDOFF.md` | Handoff gốc: list fix + backlog + audit SLIDE |
| `PORT_4.14.md` | Spec layout 4.14 |
| `KET_LUAN_4.14.md` | Nhật ký kết luận từng chặng (A→G), gồm chặng G: hình học + bug words_per_set |
| `AUDIT_GEOMETRY.md` | Dẫn chứng shift 8 vs 12 |
| `geom_scan*.py`, `analyze_one.py`, `filter_geom.py` | Công cụ quét syscall/địa chỉ copy offline |
| `extract_lk2.py`, `analyze_lk.py`, `show_crash.py` | Đọc panic trace `/data/log/dumpstate_lastkmsg_*.log.gz` |
| `build32.sh`, `build14.sh` | Build con armhf (compat) và cha aarch64 |
| `~/ghostlock/ghostlock-oneplus` | Repo exploit (đã sửa cho 4.14, chưa commit) |
| `~/ghostlock/kernel/Image`, `kallsyms_fixed.txt` | Disasm + symbol ground truth |
| `~/ghostlock/src/g9700` | Source kernel 4.14 của máy |

---

## 7. CẬP NHẬT (chặng 7) — route `setsockopt` ĐÃ TRÚNG

- Thay `select` bằng **`setsockopt(level=SOL_SOCKET, optname=1000)`**: buffer 256B
  trên kernel stack tại **offset CỐ ĐỊNH** `SP0-0x1c0` (không cần đoán `shift`).
- `waiter = SP0-0x1b0`, `task@+0x30 lock@+0x38` ⇒ **`task@buf[0x40]`, `lock@buf[0x48]`**.
- **Đã xác nhận trên máy** (panic `kp27`):
  ```
  Unable to handle kernel paging request at virtual address ffffffc800000000
  pc : _raw_spin_trylock+0x1c
  lr : rt_mutex_adjust_prio_chain+0x244
  x24: ffffffc800000000   ← waiter->lock = fake_lock (kiểm soát được!)
  x25: ffffff8021f6bd10   ← waiter (stack T)
  ```
  ⇒ paint **trúng byte**, walk đọc đúng `waiter->lock`.
- Bẫy đã vượt: **race thứ tự** — consumer phải bắn **sau** khi `setsockopt` copy xong
  (đặt `punch_consume_go` sau paint + `usleep(20ms)`).
- Hệ quả: bỏ được `shift`, bỏ ABI 32-bit, bỏ bitmap `res_*` ⇒ route gọn hơn hẳn.

**Đang làm:** tích hợp route này vào flow đầy đủ (cha spray trang giả tại `fake_lock`)
để walk đi qua `trylock` → thao tác rb-tree (**PI write**).

---

*Ngày: 2026-10-09. Trạng thái: paint TRÚNG (`lock` = giá trị kiểm soát); còn lại là
cấp trang giả hợp lệ để hoàn tất PI write.*
